import typing as tp

import github
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


def _parse_github_repo(repo) -> models.GithubRepo:
    return models.GithubRepo(
        name=repo.name,
        url=repo.html_url,
        zipball_url=repo.get_archive_link('zipball'),
        num_stars=repo.stargazers_count)


def load_github_repo(engine, github_repo: models.GithubRepo) -> None:
    db.save_github_repo(engine, github_repo)
