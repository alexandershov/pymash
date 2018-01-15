import glob
import multiprocessing
import os
import random
import re
import tempfile
import typing as tp
import urllib.request as urllib_request
import zipfile

import github

from pymash import cfg
from pymash import db
from pymash import loggers
from pymash import models
from pymash import parser
from pymash import type_aliases as ta
from pymash import utils
from pymash.scripts import base


class Selector:
    BAD_FUNCTION_NAME_RE = re.compile('test|assert', re.IGNORECASE)
    MAX_LINE_LENGTH = 120
    MAX_NUM_COMMENT_LINES = 5
    MIN_NUM_LINES = 3
    MAX_NUM_LINES = 20
    NUM_OF_FUNCTIONS_PER_REPO = 1000


@utils.log_time(loggers.loader)
def load_most_popular(
        engine: ta.Engine, language: str, limit: int,
        whitelisted_full_names: ta.SetOfStrings = (),
        blacklisted_full_names: ta.SetOfStrings = (),
        concurrency: int = 1) -> None:
    github_client = _get_github_client()
    github_repos = find_most_popular_github_repos(github_client, language, limit)
    github_repos.extend(_find_github_repos(github_client, whitelisted_full_names))
    github_repos = _exclude_blacklisted(github_repos, blacklisted_full_names)

    loaded_repos = load_many_github_repos(github_repos, concurrency=concurrency)
    db.deactivate_all_other_repos(engine, loaded_repos)


def _find_github_repos(github_client, full_names) -> ta.GithubRepos:
    github_repos = []
    log_msg = f'loading {len(full_names)} github repos'
    with utils.log_time(loggers.loader, log_msg):
        for a_full_name in full_names:
            a_github_repo = github_client.get_repo(a_full_name, lazy=False)
            github_repos.append(_parse_github_repo(a_github_repo))
    return github_repos


def _exclude_blacklisted(
        github_repos: tp.List[models.GithubRepo], blacklisted_full_names) -> tp.List[models.GithubRepo]:
    return [
        a_github_repo
        for a_github_repo in github_repos
        if a_github_repo.full_name not in blacklisted_full_names
    ]


@utils.log_time(loggers.loader)
def find_most_popular_github_repos(github_client, language: str, limit: int) -> tp.List[models.GithubRepo]:
    loggers.loader.info('finding %d most popular %s repos', limit, language)
    repositories = github_client.search_repositories(f'language:{language}', sort='stars')
    return list(map(_parse_github_repo, repositories[:limit]))


def _get_github_client():
    config = cfg.get_config()
    return github.Github(config.github_token)


def _parse_github_repo(github_repo) -> models.GithubRepo:
    return models.GithubRepo(
        github_id=github_repo.id,
        name=github_repo.name,
        full_name=github_repo.full_name,
        url=github_repo.html_url,
        zipball_url=github_repo.get_archive_link('zipball'),
        num_stars=github_repo.stargazers_count)


@utils.log_time(loggers.loader)
def _unzip_file(path, output_dir):
    with zipfile.ZipFile(path) as z:
        z.extractall(path=output_dir)


@utils.log_time(
    loggers.loader,
    lambda github_repos, concurrency: f'{len(github_repos)} github repos with concurrency {concurrency}')
def load_many_github_repos(github_repos: tp.List[models.GithubRepo], concurrency: int) -> tp.List[models.Repo]:
    loggers.loader.info('will load %d repos with concurrency %d', len(github_repos), concurrency)
    pool = multiprocessing.Pool(concurrency)
    return pool.map(load_github_repo, github_repos)


# TODO: maybe separate parsing & saving to database
@utils.log_time(loggers.loader)
def load_github_repo(github_repo: models.GithubRepo) -> models.Repo:
    loggers.loader.info('loading repo %s', github_repo.full_name)
    with base.ScriptContext() as context:
        functions = set()
        with tempfile.NamedTemporaryFile() as temp_file:
            repo = db.upsert_repo(context.engine, github_repo)
            with utils.log_time(loggers.loader, f'fetching {github_repo.zipball_url}'):
                urllib_request.urlretrieve(github_repo.zipball_url, temp_file.name)
            with tempfile.TemporaryDirectory() as temp_dir:
                with utils.log_time(loggers.loader, f'unzipping {temp_file.name}'):
                    _unzip_file(temp_file.name, temp_dir)
                with utils.log_time(loggers.loader, f'parsing {github_repo.url}'):
                    py_files = list(_find_files(temp_dir, 'py'))
                    for a_file in py_files:
                        with open(a_file, encoding='utf-8') as fileobj:
                            file_functions = parser.get_functions(fileobj, catch_exceptions=True)
                            functions.update(file_functions)
        loggers.loader.info(
            'found %d distinct functions in %d files',
            len(functions), len(py_files))
        with utils.log_time(loggers.loader, f'select functions from {len(functions)}'):
            good_functions = select_good_functions(functions)
            loggers.loader.info(
                'selected %d/%d good functions',
                len(good_functions), len(functions))
            functions_to_update = _select_random_functions(good_functions)
            loggers.loader.info(
                'selected %d/%d random functions',
                len(functions_to_update), len(good_functions))

        db.update_functions(context.engine, repo, functions_to_update)
        return repo


def _select_random_functions(functions: tp.List[parser.Function]) -> tp.List[parser.Function]:
    return random.sample(functions, min(Selector.NUM_OF_FUNCTIONS_PER_REPO, len(functions)))


def _find_files(directory, extension):
    files = []
    pattern = os.path.join(directory, f'**/*.{extension}')
    for path in glob.iglob(pattern, recursive=True):
        full_path = os.path.join(directory, path)
        files.append(full_path)
    return files


def select_good_functions(functions: tp.Iterable[parser.Function]) -> tp.List[parser.Function]:
    return [
        a_function
        for a_function in functions
        if not _is_bad_function(a_function)
    ]


def _is_bad_function(fn: parser.Function) -> bool:
    if Selector.BAD_FUNCTION_NAME_RE.search(fn.name) is not None:
        return True
    lines = fn.text.splitlines()
    if len(lines) < Selector.MIN_NUM_LINES:
        return True
    if len(lines) > Selector.MAX_NUM_LINES:
        return True
    has_too_long_line = any(len(a_line) > Selector.MAX_LINE_LENGTH for a_line in lines)
    if has_too_long_line:
        return True
    num_comment_lines = sum(1 for a_line in lines if parser.is_comment_line(a_line))
    if num_comment_lines > Selector.MAX_NUM_COMMENT_LINES:
        return True
    return False
