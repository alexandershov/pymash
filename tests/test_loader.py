import os
import typing as tp
from unittest import mock

import github

from pymash import db
from pymash import loader
from pymash import models
from pymash.tables import *


def test_load_most_popular(pymash_engine, monkeypatch):
    archive_link_mock = mock.Mock(return_value=_make_data_dir_path('file_with_two_functions.py.zip'))
    github_client_repos = [
        mock.Mock(
            id=1001,
            html_url='https://github.com/django/django',
            get_archive_link=archive_link_mock,
            stargazers_count=25000),
        mock.Mock(
            id=1002,
            html_url='https://github.com/pallets/flask',
            get_archive_link=archive_link_mock,
            stargazers_count=26000),
    ]
    # TODO: is there a better way? (name kwarg conflicts with the Mock.name attribute for __repr__)
    github_client_repos[0].name = 'django'
    github_client_repos[1].name = 'flask'
    github_mock = mock.Mock()
    github_mock.return_value.search_repositories.return_value = github_client_repos
    monkeypatch.setattr(github, 'Github', github_mock)
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
        conn.execute(Functions.insert().values({
            Functions.c.function_id: 888,
            Functions.c.repo_id: 2,
            Functions.c.text: 'def mul(x, y):\n    return x * y',
            Functions.c.is_active: True,
            Functions.c.random: 0.7,
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
        django_rows = list(conn.execute(Functions.select(Functions.c.repo_id != 2)))
        flask_rows = list(conn.execute(Functions.select(Functions.c.repo_id == 2)))
    assert len(rows) == 5
    assert len(django_rows) == 2
    assert len(flask_rows) == 3
    django_functions = list(map(db.make_function_from_db_row, django_rows))
    flask_functions = list(map(db.make_function_from_db_row, flask_rows))
    assert _group_by_text(django_functions) == {
        'def add(x, y):\n    return x + y': True,
        'def sub(x, y):\n    return x - y': True,
    }
    assert _group_by_text(flask_functions) == {
        'def add(x, y):\n    return x + y': True,
        'def sub(x, y):\n    return x - y': True,
        'def mul(x, y):\n    return x * y': False,
    }


def _group_by_text(functions: tp.List[models.Function]):
    assert len({a_function.text for a_function in functions}) == len(functions)
    return {
        a_function.text: a_function.is_active
        for a_function in functions
    }


def _make_data_dir_path(relative_name):
    return 'file://' + os.path.join(os.path.dirname(__file__), 'data', relative_name)
