import glob
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
from pymash import utils

_NUM_OF_FUNCTIONS_PER_REPO = 1000
_BAD_FUNCTION_NAME_RE = re.compile('test|assert', re.IGNORECASE)


@utils.log_time(loggers.loader)
def load_most_popular(engine, language, limit, extra_repos_full_names=()):
    github_client = _get_github_client()
    github_repos = find_most_popular_github_repos(github_client, language, limit)
    with utils.log_time(loggers.loader, f'loading {len(extra_repos_full_names)} extra repos'):
        for full_name in extra_repos_full_names:
            # TODO: maybe pass lazy=False to the github_client.get_repo
            github_repos.append(_parse_github_repo(github_client.get_repo(full_name)))
    load_many_github_repos(engine, github_repos)
    # TODO: you need to deactivate all functions from repos that were in db but
    # in most_popular_list & probably deactivate these repos and don't show them in a /leaders list


@utils.log_time(loggers.loader)
def find_most_popular_github_repos(github_client, language: str, limit: int) -> tp.List[models.GithubRepo]:
    repositories = github_client.search_repositories(f'language:{language}', sort='stars')
    return list(map(_parse_github_repo, repositories[:limit]))


def _get_github_client():
    config = cfg.get_config()
    return github.Github(config.github_token)


def _parse_github_repo(github_repo) -> models.GithubRepo:
    return models.GithubRepo(
        github_id=github_repo.id,
        name=github_repo.name,
        url=github_repo.html_url,
        zipball_url=github_repo.get_archive_link('zipball'),
        num_stars=github_repo.stargazers_count)


@utils.log_time(loggers.loader)
def _unzip_file(path, output_dir):
    with zipfile.ZipFile(path) as z:
        z.extractall(path=output_dir)


@utils.log_time(loggers.loader, lambda engine, github_repos: f'{len(github_repos)} github repos')
def load_many_github_repos(engine, github_repos: tp.List[models.GithubRepo]) -> None:
    for a_github_repo in github_repos:
        load_github_repo(engine, a_github_repo)


@utils.log_time(loggers.loader)
def load_github_repo(engine, github_repo: models.GithubRepo) -> None:
    functions = []
    with tempfile.NamedTemporaryFile() as temp_file:
        repo = db.save_github_repo(engine, github_repo)
        with utils.log_time(loggers.loader, f'fetching {github_repo.zipball_url}'):
            urllib_request.urlretrieve(github_repo.zipball_url, temp_file.name)
        with tempfile.TemporaryDirectory() as temp_dir:
            with utils.log_time(loggers.loader, f'unzipping {temp_file.name}'):
                _unzip_file(temp_file.name, temp_dir)
            with utils.log_time(loggers.loader, f'parsing {github_repo.url}'):
                for a_file in _find_files(temp_dir, 'py'):
                    with open(a_file, encoding='utf-8') as fileobj:
                        try:
                            source = fileobj.read()
                        # TODO: test this
                        except UnicodeDecodeError:
                            continue
                    try:
                        file_functions = parser.get_functions(source, catch_exceptions=True)
                    except SyntaxError:
                        # TODO: test SyntaxError
                        loggers.loader.error('could not parse %s', a_file, exc_info=True)
                    else:
                        # TODO: add only unique functions
                        functions.extend(file_functions)
    with utils.log_time(loggers.loader, f'select functions from {len(functions)}'):
        # TODO: pick the most suitable functions
        # TODO: test that random.sample applies only to all function (not file_functions)
        good_functions = select_good_functions(functions)
        functions_to_update = random.sample(
            good_functions, min(_NUM_OF_FUNCTIONS_PER_REPO, len(good_functions)))
    db.update_functions(engine, repo, functions_to_update)


def _find_files(directory, extension):
    files = []
    pattern = os.path.join(directory, f'**/*.{extension}')
    for path in glob.iglob(pattern, recursive=True):
        full_path = os.path.join(directory, path)
        files.append(full_path)
    return files


def select_good_functions(functions: tp.List[parser.Function]) -> tp.List[parser.Function]:
    return [
        a_function
        for a_function in functions
        if not _is_bad_function(a_function)
    ]


def _is_bad_function(fn: parser.Function) -> bool:
    if _BAD_FUNCTION_NAME_RE.search(fn.name) is not None:
        return True
    return False
