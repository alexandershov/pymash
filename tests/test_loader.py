import os
import textwrap
import typing as tp
from unittest import mock

import github
import pytest
import sqlalchemy as sa

from pymash import db
from pymash import loader
from pymash import models
from pymash import parser
from pymash.tables import *


def test_load_most_popular(pymash_engine, monkeypatch):
    archive_link_mock = mock.Mock(return_value=_make_data_dir_path('file_with_two_functions.py.zip'))
    github_client_repos = [
        _make_mock(
            id=1001,
            name='django',
            html_url='https://github.com/django/django',
            get_archive_link=archive_link_mock,
            stargazers_count=25000),
        _make_mock(
            id=1002,
            name='flask',
            html_url='https://github.com/pallets/flask',
            get_archive_link=archive_link_mock,
            stargazers_count=26000),
    ]
    pymash_mock = _make_mock(
        id=1003,
        name='pymash',
        html_url='https://github.com/alexandershov/pymash',
        get_archive_link=archive_link_mock,
        stargazers_count=1)
    github_mock = mock.Mock()
    github_mock.return_value.search_repositories.return_value = github_client_repos
    github_mock.return_value.get_repo.return_value = pymash_mock
    monkeypatch.setattr(github, 'Github', github_mock)
    _add_data(pymash_engine)
    loader.load_most_popular(pymash_engine, 'python', 1000, extra_repos_full_names=['alexandershov/pymash'])
    _assert_repo_was_loaded(pymash_engine)
    _assert_functions_were_loaded(pymash_engine)


@pytest.mark.parametrize('source_code, expected_names', [
    # we ignore functions with bad names
    (
            '''
            def teSt_add(x, y):
                assert x == y
                
            def assErt_equal(x, y):
                assert_equal(x, y)
            ''',
            [],
    ),
])
def test_select_good_functions(source_code, expected_names):
    functions = parser.get_functions(textwrap.dedent(source_code))
    good_functions = loader.select_good_functions(functions)
    actual_names = {a_function.name for a_function in good_functions}
    assert actual_names == set(expected_names)


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
        pymash_row = list(conn.execute(Repos.select().where(Repos.c.github_id == 1003)))[0]
    assert len(rows) == 3

    django_repo = db.make_repo_from_db_row(django_row)
    assert django_repo.name == 'django'
    assert django_repo.url == 'https://github.com/django/django'
    assert django_repo.rating == models.Repo.DEFAULT_RATING

    flask_repo = db.make_repo_from_db_row(flask_row)
    assert flask_repo.name == 'flask'
    assert flask_repo.url == 'https://github.com/pallets/flask'
    assert flask_repo.rating == 1900

    pymash_repo = db.make_repo_from_db_row(pymash_row)
    assert pymash_repo.name == 'pymash'
    assert pymash_repo.url == 'https://github.com/alexandershov/pymash'
    assert pymash_repo.rating == 1800


def _assert_functions_were_loaded(pymash_engine):
    with pymash_engine.connect() as conn:
        rows = list(conn.execute(Functions.select()))
        django_rows = list(conn.execute(
            Functions.join(Repos, sa.and_(Functions.c.repo_id == Repos.c.repo_id, Repos.c.name == 'django')).select()))
        flask_rows = list(conn.execute(
            Functions.join(Repos, sa.and_(Functions.c.repo_id == Repos.c.repo_id, Repos.c.name == 'flask')).select()))
        pymash_rows = list(conn.execute(
            Functions.join(Repos, sa.and_(Functions.c.repo_id == Repos.c.repo_id, Repos.c.name == 'pymash')).select()))
    assert len(rows) == 7
    assert len(django_rows) == 2
    assert len(flask_rows) == 3
    assert len(pymash_rows) == 2
    django_functions = list(map(db.make_function_from_db_row, django_rows))
    flask_functions = list(map(db.make_function_from_db_row, flask_rows))
    pymash_functions = list(map(db.make_function_from_db_row, pymash_rows))
    assert _group_by_text(django_functions) == {
        'def add(x, y):\n    return x + y': True,
        'def sub(x, y):\n    return x - y': True,
    }
    assert _group_by_text(flask_functions) == {
        'def add(x, y):\n    return x + y': True,
        'def sub(x, y):\n    return x - y': True,
        'def mul(x, y):\n    return x * y': False,
    }
    assert _group_by_text(pymash_functions) == {
        'def add(x, y):\n    return x + y': True,
        'def sub(x, y):\n    return x - y': True,
    }


def _group_by_text(functions: tp.List[models.Function]):
    assert len({a_function.text for a_function in functions}) == len(functions)
    return {
        a_function.text: a_function.is_active
        for a_function in functions
    }


def _make_data_dir_path(relative_name):
    return 'file://' + os.path.join(os.path.dirname(__file__), 'data', relative_name)


def _make_mock(**kwargs):
    m = mock.Mock()
    m.configure_mock(**kwargs)
    return m
