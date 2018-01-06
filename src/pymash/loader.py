import typing as tp

from pymash import db
from pymash import models


def load_most_popular(engine):
    repos = find_most_popular_github_repos()
    for a_repo in repos:
        load_github_repo(engine, a_repo)


def find_most_popular_github_repos() -> tp.List[models.GithubRepo]:
    # TODO: implement it via github API
    raise NotImplementedError


def load_github_repo(engine, github_repo: models.GithubRepo) -> None:
    db.save_github_repo(engine, github_repo)
