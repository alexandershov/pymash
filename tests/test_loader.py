from unittest import mock

from pymash import loader
from pymash import models
from pymash.tables import *


def _test_load_most_popular(pymash_engine, monkeypatch):
    find_mock = mock.Mock(return_value=[
        models.GithubRepo(
            name='django',
            url='https://github.com/django/django',
            num_stars=25000)])
    monkeypatch.setattr(loader, 'find_most_popular_github_repos', find_mock)
    loader.load_most_popular(pymash_engine)
    _assert_repo_was_loaded(pymash_engine)


def _assert_repo_was_loaded(pymash_engine):
    with pymash_engine.connect() as conn:
        rows = list(conn.execute(Repos.select()))
    assert len(rows) == 1
