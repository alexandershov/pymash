from unittest import mock

import os

from pymash import db
from pymash import loader
from pymash import models
from pymash.tables import *


def test_load_most_popular(pymash_engine, monkeypatch):
    find_mock = mock.Mock(return_value=[
        models.GithubRepo(
            github_id=1001,
            name='django',
            url='https://github.com/django/django',
            zipball_url=_make_data_dir_path('file_with_two_functions.py.zip'),
            num_stars=25000),
        models.GithubRepo(
            github_id=1002,
            name='flask',
            url='https://github.com/pallets/flask',
            zipball_url=_make_data_dir_path('file_with_two_functions.py.zip'),
            num_stars=26000)])
    monkeypatch.setattr(loader, 'find_most_popular_github_repos', find_mock)
    _add_data(pymash_engine)
    loader.load_most_popular(pymash_engine, 'python', 1000)
    _assert_repo_was_loaded(pymash_engine)
    _assert_functions_were_loaded(pymash_engine)


def _add_data(pymash_engine):
    with pymash_engine.connect() as conn:
        conn.execute(Repos.insert().values({
            Repos.c.repo_id: 2,
            Repos.c.github_id: 1002,
            Repos.c.name: 'flask',
            Repos.c.url: 'https://github.com/pallets/flask',
            Repos.c.rating: 1900,
        }))
        conn.execute(Functions.insert().values({
            Functions.c.function_id: 777,
            Functions.c.repo_id: 2,
            Functions.c.text: 'def add(x, y):\n    return x + y',
            Functions.c.is_active: True,
            Functions.c.random: 0.6,
        }))


def _assert_repo_was_loaded(pymash_engine):
    with pymash_engine.connect() as conn:
        rows = list(conn.execute(Repos.select()))
        django_row = list(conn.execute(Repos.select().where(Repos.c.github_id == 1001)))[0]
        flask_row = list(conn.execute(Repos.select().where(Repos.c.github_id == 1002)))[0]
    assert len(rows) == 2

    django_repo = db.make_repo_from_db_row(django_row)
    assert django_repo.name == 'django'
    assert django_repo.url == 'https://github.com/django/django'
    assert django_repo.rating == models.Repo.DEFAULT_RATING

    flask_repo = db.make_repo_from_db_row(flask_row)
    assert flask_repo.name == 'flask'
    assert flask_repo.url == 'https://github.com/pallets/flask'
    assert flask_repo.rating == 1900


def _assert_functions_were_loaded(pymash_engine):
    with pymash_engine.connect() as conn:
        rows = list(conn.execute(Functions.select()))
    # TODO: check fields
    assert len(rows) == 4


def _make_data_dir_path(relative_name):
    return 'file://' + os.path.join(os.path.dirname(__file__), 'data', relative_name)
