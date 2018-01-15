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
    github_repos = _find_most_popular_github_repos(github_client, language, limit)
    github_repos.extend(_find_github_repos(github_client, whitelisted_full_names))
    github_repos = _exclude_blacklisted(github_repos, blacklisted_full_names)

    loaded_repos = _load_many_github_repos(github_repos, concurrency=concurrency)
    db.deactivate_all_other_repos(engine, loaded_repos)


def _find_github_repos(github_client, full_names) -> ta.GithubRepos:
    github_repos = []
    log_msg = f'loading {len(full_names)} github repos'
    with utils.log_time(loggers.loader, log_msg):
        for a_full_name in full_names:
            repository = github_client.get_repo(a_full_name, lazy=False)
            github_repos.append(_parse_repository(repository))
    return github_repos


def _exclude_blacklisted(
        github_repos: ta.GithubRepos, blacklisted_full_names) -> ta.GithubRepos:
    return [
        a_github_repo
        for a_github_repo in github_repos
        if a_github_repo.full_name not in blacklisted_full_names
    ]


@utils.log_time(loggers.loader)
def _find_most_popular_github_repos(
        github_client, language: str, limit: int) -> ta.GithubRepos:
    loggers.loader.info('finding %d most popular %s repos', limit, language)
    repositories = github_client.search_repositories(f'language:{language}', sort='stars')
    return list(map(_parse_repository, repositories[:limit]))


def _get_github_client():
    config = cfg.get_config()
    return github.Github(config.github_token)


def _parse_repository(repository: ta.Repository) -> models.GithubRepo:
    return models.GithubRepo(
        github_id=repository.id,
        name=repository.name,
        full_name=repository.full_name,
        url=repository.html_url,
        zipball_url=repository.get_archive_link('zipball'),
        num_stars=repository.stargazers_count)


@utils.log_time(loggers.loader)
def _unzip_file(path: str, output_dir: str) -> None:
    with zipfile.ZipFile(path) as z:
        z.extractall(path=output_dir)


@utils.log_time(
    loggers.loader,
    lambda github_repos, concurrency: f'{len(github_repos)} github repos, concurrency {concurrency}')
def _load_many_github_repos(github_repos: ta.GithubRepos, concurrency: int) -> ta.Repos:
    loggers.loader.info(
        'will load %d github repos, concurrency %d', len(github_repos), concurrency)
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
                    py_files = _find_files(temp_dir, 'py')
                    for a_file in py_files:
                        with open(a_file, encoding='utf-8') as fileobj:
                            file_functions = parser.get_functions(fileobj, catch_exceptions=True)
                            functions.update(file_functions)
        loggers.loader.info(
            'found %d distinct functions in %d files',
            len(functions), len(py_files))

        functions_to_update = _select_functions_to_update(functions)
        db.update_functions(context.engine, repo, functions_to_update)
        return repo


def _select_functions_to_update(functions: tp.Set[parser.Function]) -> ta.ParserFunctions:
    with utils.log_time(loggers.loader, f'select functions from {len(functions)}'):
        good_functions = select_good_functions(functions)
        loggers.loader.info('selected %d/%d good functions', len(good_functions), len(functions))
        result = _select_random_functions(good_functions)
        loggers.loader.info('selected %d/%d random functions', len(result), len(good_functions))
    return result


def _select_random_functions(functions: tp.List[parser.Function]) -> tp.List[parser.Function]:
    num_functions = min(Selector.NUM_OF_FUNCTIONS_PER_REPO, len(functions))
    return random.sample(functions, num_functions)


def _find_files(directory, extension):
    files = []
    pattern = os.path.join(directory, f'**/*.{extension}')
    for path in glob.iglob(pattern, recursive=True):
        full_path = os.path.join(directory, path)
        files.append(full_path)
    return files


def select_good_functions(functions: tp.Iterable[parser.Function]) -> ta.ParserFunctions:
    return [
        a_function
        for a_function in functions
        if not _is_bad_function(a_function)
    ]


def _is_bad_function(fn: parser.Function) -> bool:
    checks = [
        _has_bad_name,
        _is_too_short,
        _is_too_long,
        _has_too_long_line,
        _has_too_many_comment_lines,
    ]
    if any(a_check(fn) for a_check in checks):
        return True
    return False


def _has_bad_name(fn: parser.Function) -> bool:
    return Selector.BAD_FUNCTION_NAME_RE.search(fn.name) is not None


def _is_too_short(fn: parser.Function) -> bool:
    return len(fn.lines) < Selector.MIN_NUM_LINES


def _is_too_long(fn: parser.Function) -> bool:
    return len(fn.lines) > Selector.MAX_NUM_LINES


def _has_too_long_line(fn: parser.Function) -> bool:
    return any(len(a_line) > Selector.MAX_LINE_LENGTH for a_line in fn.lines)


def _has_too_many_comment_lines(fn: parser.Function) -> bool:
    num_comment_lines = sum(1 for a_line in fn.lines if parser.is_comment_line(a_line))
    return num_comment_lines > Selector.MAX_NUM_COMMENT_LINES
