import io
import os
import random
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
    archive_with_two_functions = mock.Mock(return_value=_make_data_dir_path('repo_with_three_functions.py.zip'))
    archive_with_three_functions = mock.Mock(return_value=_make_data_dir_path('repo_with_two_functions.py.zip'))
    github_client_repos = [
        _make_mock(
            id=1001,
            name='django',
            full_name='django/django',
            html_url='https://github.com/django/django',
            get_archive_link=archive_with_three_functions,
            stargazers_count=25000),
        _make_mock(
            id=1002,
            name='flask',
            full_name='pallets/flask',
            html_url='https://github.com/pallets/flask',
            get_archive_link=archive_with_two_functions,
            stargazers_count=26000),
        _make_mock(
            id=1004,
            name='CppCoreGuideLines',
            full_name='isocpp/CppCoreGuidelines',
            html_url='https://github.com/isocpp/CppCoreGuidelines',
            get_archive_link=archive_with_two_functions,
            stargazers_count=33000)
    ]
    pymash_mock = _make_mock(
        id=1003,
        name='pymash',
        full_name='alexandershov/pymash',
        html_url='https://github.com/alexandershov/pymash',
        get_archive_link=archive_with_two_functions,
        stargazers_count=1)
    github_mock = mock.Mock()
    github_mock.return_value.search_repositories.return_value = github_client_repos
    github_mock.return_value.get_repo.return_value = pymash_mock
    monkeypatch.setattr(github, 'Github', github_mock)
    orig_random_sample = random.sample

    def _mock_random_sample(population, k):
        if len(population) == k:
            return orig_random_sample(population, k)
        assert len(population) == k + 1
        result = [a_function for a_function in population if a_function.name != 'zzz']
        assert len(result) == len(population) - 1
        return result

    monkeypatch.setattr(random, 'sample', _mock_random_sample)

    _add_data(pymash_engine)
    loader.load_most_popular(
        pymash_engine, 'python', 1000,
        whitelisted_full_names={'alexandershov/pymash'},
        blacklisted_full_names={'isocpp/CppCoreGuidelines'},
        concurrency=2,
    )
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
    # we ignore functions with too long lines
    (
            f'''
            def add(x, y):
                s = {'x' * 200} 
                return x + y
            ''',
            [],
    ),
    # we ignore functions with too many comments
    (
            '''
            def add(x, y):
                # 1
                # 2
                # 3
                return x + y
            ''',
            [],
    ),
    # we ignore functions with too many lines
    (
            '''def add(x, y):
                    2
                    3
                    4
                    5
                    6
                    7
                    8
            ''',
            [],
    ),
    # we ignore functions with too few lines
    (
            '''def add(x, y): return x + y''',
            [],
    ),
])
def test_select_good_functions(source_code, expected_names):
    functions = parser.get_functions(io.StringIO(textwrap.dedent(source_code)))
    good_functions = loader.select_good_functions(functions)
    actual_names = {a_function.name for a_function in good_functions}
    assert actual_names == set(expected_names)


def _add_data(pymash_engine):
    with pymash_engine.connect() as conn:
        conn.execute(Repos.insert().values({
            Repos.c.repo_id: -2,
            Repos.c.github_id: 1002,
            Repos.c.name: 'flask',
            Repos.c.url: 'https://github.com/pallets/flask',
            Repos.c.is_active: True,
            Repos.c.rating: 1900,
        }))
        conn.execute(Functions.insert().values({
            Functions.c.function_id: 777,
            Functions.c.repo_id: -2,
            Functions.c.text: 'def add(x, y):\n    return x + y',
            Functions.c.is_active: True,
            Functions.c.random: 0.6,
        }))
        conn.execute(Functions.insert().values({
            Functions.c.function_id: 888,
            Functions.c.repo_id: -2,
            Functions.c.text: 'def mul(x, y):\n    return x * y',
            Functions.c.is_active: True,
            Functions.c.random: 0.7,
        }))
        conn.execute(Repos.insert().values({
            Repos.c.repo_id: -5,
            Repos.c.github_id: 1005,
            Repos.c.name: 'requests',
            Repos.c.url: 'https://github.com/requests/requests',
            Repos.c.is_active: True,
            Repos.c.rating: 2000,
        }))
        conn.execute(Functions.insert().values({
            Functions.c.function_id: 999,
            Functions.c.repo_id: -5,
            Functions.c.text: 'def add(x, y):\n    return x + y',
            Functions.c.is_active: True,
            Functions.c.random: 0.8,
        }))


def _assert_repo_was_loaded(pymash_engine):
    with pymash_engine.connect() as conn:
        rows = list(conn.execute(Repos.select()))
        django_row = conn.execute(Repos.select().where(Repos.c.github_id == 1001)).first()
        flask_row = conn.execute(Repos.select().where(Repos.c.github_id == 1002)).first()
        pymash_row = conn.execute(Repos.select().where(Repos.c.github_id == 1003)).first()
        requests_row = conn.execute(Repos.select().where(Repos.c.github_id == 1005)).first()
    assert len(rows) == 4

    django_repo = db.make_repo_from_db_row(django_row)
    assert django_repo.name == 'django'
    assert django_repo.url == 'https://github.com/django/django'
    assert django_repo.is_active
    assert django_repo.rating == models.Repo.DEFAULT_RATING

    flask_repo = db.make_repo_from_db_row(flask_row)
    assert flask_repo.name == 'flask'
    assert flask_repo.url == 'https://github.com/pallets/flask'
    assert flask_repo.is_active
    assert flask_repo.rating == 1900

    pymash_repo = db.make_repo_from_db_row(pymash_row)
    assert pymash_repo.name == 'pymash'
    assert pymash_repo.url == 'https://github.com/alexandershov/pymash'
    assert pymash_repo.is_active
    assert pymash_repo.rating == 1800

    requests_repo = db.make_repo_from_db_row(requests_row)
    assert requests_repo.name == 'requests'
    assert requests_repo.url == 'https://github.com/requests/requests'
    assert not requests_repo.is_active
    assert requests_repo.rating == 2000


def _assert_functions_were_loaded(pymash_engine):
    with pymash_engine.connect() as conn:
        rows = list(conn.execute(Functions.select()))
        django_rows = _find_functions_with_repo_name(conn, 'django')
        flask_rows = _find_functions_with_repo_name(conn, 'flask')
        pymash_rows = _find_functions_with_repo_name(conn, 'pymash')
        requests_rows = _find_functions_with_repo_name(conn, 'requests')
    assert len(rows) == 8
    assert len(django_rows) == 2
    assert len(flask_rows) == 3
    assert len(requests_rows) == 1
    django_functions = list(map(db.make_function_from_db_row, django_rows))
    flask_functions = list(map(db.make_function_from_db_row, flask_rows))
    pymash_functions = list(map(db.make_function_from_db_row, pymash_rows))
    requests_functions = list(map(db.make_function_from_db_row, requests_rows))
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
    assert _group_by_text(requests_functions) == {
        'def add(x, y):\n    return x + y': False,
    }


def _find_functions_with_repo_name(conn, repo_name):
    return list(conn.execute(
        Functions.join(Repos, sa.and_(Functions.c.repo_id == Repos.c.repo_id, Repos.c.name == repo_name)).select()))


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
