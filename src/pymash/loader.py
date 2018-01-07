import tempfile
import typing as tp
import urllib.request as urllib_request
import zipfile

import github
import os

from pymash import cfg
from pymash import db
from pymash import models


def load_most_popular(engine, language, limit):
    repos = find_most_popular_github_repos(language, limit)
    for a_repo in repos:
        load_github_repo(engine, a_repo)


def find_most_popular_github_repos(language: str, limit: int) -> tp.List[models.GithubRepo]:
    config = cfg.get_config()
    github_client = github.Github(config.github_token)
    repositories = github_client.search_repositories(f'language:{language}', sort='stars')
    return list(map(_parse_github_repo, repositories[:limit]))


def _parse_github_repo(github_repo) -> models.GithubRepo:
    return models.GithubRepo(
        github_id=github_repo.id,
        name=github_repo.name,
        url=github_repo.html_url,
        zipball_url=github_repo.get_archive_link('zipball'),
        num_stars=github_repo.stargazers_count)


def _unzip_file(path, output_dir):
    with zipfile.ZipFile(path) as z:
        z.extractall(path=output_dir)


def load_github_repo(engine, github_repo: models.GithubRepo) -> None:
    with tempfile.TemporaryFile() as temp_file:
        db.save_github_repo(engine, github_repo)
        return
        urllib_request.urlretrieve(github_repo.zipball_url, temp_file.name)
        with tempfile.TemporaryDirectory() as temp_dir:
            _unzip_file(temp_file.name, temp_dir.name)
