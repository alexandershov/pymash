from unittest import mock

import os

from pymash import loader
from pymash import models
from pymash.tables import *


def test_load_most_popular(pymash_engine, monkeypatch):
    find_mock = mock.Mock(return_value=[
        models.GithubRepo(
            github_id=1,
            name='django',
            url='https://github.com/django/django',
            zipball_url=_make_data_dir_path('file_with_two_functions.py.zip'),
            num_stars=25000)])
    monkeypatch.setattr(loader, 'find_most_popular_github_repos', find_mock)
    loader.load_most_popular(pymash_engine, 'python', 1000)
    _assert_repo_was_loaded(pymash_engine)
    # TODO: uncomment
    # _assert_functions_were_loaded(pymash_engine)


def _assert_repo_was_loaded(pymash_engine):
    with pymash_engine.connect() as conn:
        rows = list(conn.execute(Repos.select()))
    # TODO: check fields
    assert len(rows) == 1


def _assert_functions_were_loaded(pymash_engine):
    with pymash_engine.connect() as conn:
        rows = list(conn.execute(Functions.select()))
    # TODO: check fields
    assert len(rows) == 2


def _make_data_dir_path(relative_name):
    return 'file://' + os.path.join(os.path.dirname(__file__), 'data', relative_name)
