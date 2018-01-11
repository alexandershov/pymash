import glob
import random
import tempfile
import typing as tp
import urllib.request as urllib_request
import zipfile

import github
import os

from pymash import cfg
from pymash import db
from pymash import loggers
from pymash import models
from pymash import parser
from pymash import utils

_NUM_OF_FUNCTIONS_PER_REPO = 1000


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
    with tempfile.NamedTemporaryFile() as temp_file:
        repo = db.save_github_repo(engine, github_repo)
        with utils.log_time(loggers.loader, f'fetching {github_repo.zipball_url}'):
            urllib_request.urlretrieve(github_repo.zipball_url, temp_file.name)
        with tempfile.TemporaryDirectory() as temp_dir:
            with utils.log_time(loggers.loader, f'unzipping {temp_file.name}'):
                _unzip_file(temp_file.name, temp_dir)
            for a_file in _find_files(temp_dir, 'py'):
                with open(a_file) as fileobj:
                    with utils.log_time(loggers.loader, f'parsing {a_file}'):
                        functions = parser.get_functions(fileobj.read(), catch_exceptions=True)
                    # TODO: pick the most suitable functions
                    with utils.log_time(loggers.loader, f'select functions from {len(functions)}'):
                        functions_to_update = random.sample(functions, min(_NUM_OF_FUNCTIONS_PER_REPO, len(functions)))
                    db.update_functions(engine, repo, functions_to_update)


def _find_files(directory, extension):
    files = []
    pattern = os.path.join(directory, f'**/*.{extension}')
    for path in glob.iglob(pattern, recursive=True):
        full_path = os.path.join(directory, path)
        files.append(full_path)
    return files
