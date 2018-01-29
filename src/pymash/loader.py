import glob
import multiprocessing
import os
import random
import re
import tempfile
import typing as tp
import zipfile

import github
import requests

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
    MIN_NUM_STATEMENTS = 4
    NUM_FUNCTIONS_PER_REPO = 1000
    MIN_NUM_FUNCTIONS_PER_REPO = 20


_NOT_IMPLEMENTED_RE = re.compile(r'raise\s+NotImplementedError')
_TEST_FILE_PATH_RE = re.compile(r'test', re.IGNORECASE)


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
        zipball_url=_get_zipball_url(repository),
        num_stars=repository.stargazers_count)


def _get_zipball_url(repository: ta.Repository) -> str:
    return repository.archive_url.format_map({'archive_format': 'zipball', '/ref': ''})


@utils.log_time(loggers.loader)
def _unzip_file(path: str, output_dir: str) -> None:
    with zipfile.ZipFile(path) as z:
        z.extractall(path=output_dir)


@utils.log_time(
    loggers.loader,
    lambda github_repos, concurrency:
    f'{len(github_repos)} github repos, concurrency {concurrency}'
)
def _load_many_github_repos(github_repos: ta.GithubRepos, concurrency: int) -> ta.Repos:
    loggers.loader.info(
        'will load %d github repos, concurrency %d', len(github_repos), concurrency)
    pool = multiprocessing.Pool(concurrency)
    maybe_repos = pool.map(load_github_repo, github_repos)
    return list(filter(None, maybe_repos))


# TODO: maybe separate parsing & saving to database
@utils.log_time(loggers.loader)
def load_github_repo(github_repo: models.GithubRepo) -> tp.Optional[models.Repo]:
    loggers.loader.info('loading repo %s', github_repo.full_name)
    with base.ScriptContext() as context:
        functions = _get_functions_from_github_repo(github_repo)
        functions_to_update = _select_functions_to_update(functions)
        if len(functions) >= Selector.MIN_NUM_FUNCTIONS_PER_REPO:
            return db.upsert_repo(context.engine, github_repo, functions_to_update)
        else:
            return None


def _get_functions_from_github_repo(github_repo: models.GithubRepo) -> tp.Set[parser.Function]:
    with tempfile.NamedTemporaryFile() as temp_file:
        with utils.log_time(loggers.loader, f'fetching {github_repo.zipball_url}'):
            _urlretrieve(github_repo.zipball_url, temp_file.name)
        return _get_functions_from_zip_archive(temp_file.name, github_repo)


def _urlretrieve(url, output_path):
    resp = requests.get(url)
    with open(output_path, 'wb') as fileobj:
        fileobj.write(resp.content)


def _get_functions_from_zip_archive(
        archive_path: str, github_repo: models.GithubRepo) -> tp.Set[parser.Function]:
    with tempfile.TemporaryDirectory() as temp_dir:
        with utils.log_time(loggers.loader, f'unzipping {archive_path}'):
            _unzip_file(archive_path, temp_dir)
        return _get_functions_from_directory(github_repo, temp_dir)


def _get_functions_from_directory(
        github_repo: models.GithubRepo, dir_path: str) -> tp.Set[parser.Function]:
    functions = set()
    with utils.log_time(loggers.loader, f'parsing {github_repo.url}'):
        py_files = _find_files(dir_path, 'py')
        for a_file in py_files:
            functions.update(parser.get_functions(a_file, catch_exceptions=True))
    loggers.loader.info(f'found %d distinct functions in %d files', len(functions), len(py_files))
    return functions


def _select_functions_to_update(functions: tp.Set[parser.Function]) -> ta.ParserFunctions:
    with utils.log_time(loggers.loader, f'select functions from {len(functions)}'):
        good_functions = select_good_functions(functions)
        loggers.loader.info('selected %d/%d good functions', len(good_functions), len(functions))
        result = _select_random_functions(good_functions)
        loggers.loader.info('selected %d/%d random functions', len(result), len(good_functions))
    return result


def _select_random_functions(functions: tp.List[parser.Function]) -> tp.List[parser.Function]:
    num_functions = min(Selector.NUM_FUNCTIONS_PER_REPO, len(functions))
    return random.sample(functions, num_functions)


def _find_files(directory: str, extension: str) -> tp.List[str]:
    files = []
    pattern = os.path.join(directory, f'**/*.{extension}')
    for matched_path in glob.iglob(pattern, recursive=True):
        full_path = os.path.join(directory, matched_path)
        rel_path = os.path.relpath(full_path, directory)
        if not _is_test_file(rel_path):
            files.append(full_path)
    return files


def select_good_functions(functions: tp.Iterable[parser.Function]) -> ta.ParserFunctions:
    return [
        a_function
        for a_function in functions
        if not _is_bad_function(a_function)
    ]


def _is_test_file(path):
    return _TEST_FILE_PATH_RE.search(path) is not None


def _is_bad_function(fn: parser.Function) -> bool:
    checks = [
        _has_bad_name,
        _is_too_short,
        _is_too_long,
        _has_too_few_statements,
        _has_too_long_line,
        _has_too_many_comment_lines,
        _raises_not_implemented_error,
        _is_init_method,
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


def _has_too_few_statements(fn: parser.Function) -> bool:
    return fn.num_statements < Selector.MIN_NUM_STATEMENTS


def _has_too_long_line(fn: parser.Function) -> bool:
    return any(len(a_line) > Selector.MAX_LINE_LENGTH for a_line in fn.lines)


def _has_too_many_comment_lines(fn: parser.Function) -> bool:
    num_comment_lines = sum(1 for a_line in fn.lines if parser.is_comment_line(a_line))
    return num_comment_lines > Selector.MAX_NUM_COMMENT_LINES


def _raises_not_implemented_error(fn: parser.Function) -> bool:
    return _NOT_IMPLEMENTED_RE.search(fn.text) is not None


def _is_init_method(fn: parser.Function) -> bool:
    return fn.name == '__init__'
