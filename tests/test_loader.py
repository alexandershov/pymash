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


def test_load_most_popular(pymash_engine, github_mock, monkeypatch):
    monkeypatch.setattr(github, 'Github', github_mock)
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


def _mock_random_sample(population, k):
    if len(population) == k:
        return population
    assert len(population) == k + 1
    result = [a_function for a_function in population if a_function.name != 'zzz']
    assert len(result) == len(population) - 1
    return result


@pytest.fixture(name='github_mock')
def fixture_github_mock():
    archive_with_four_functions_and_tests = mock.Mock(
        # one function is zzz (ignored by _random_sample_mock)
        # another function in a test file (ignored by _find_files)
        # remaining functions are okay
        return_value=_make_data_dir_path('repo_with_four_functions_and_tests.py.zip'))
    archive_with_two_functions = mock.Mock(
        # both functions are okay
        return_value=_make_data_dir_path('repo_with_two_functions.py.zip'))
    github_client_repos = [
        _make_mock(
            id=1001,
            name='django',
            full_name='django/django',
            html_url='https://github.com/django/django',
            get_archive_link=archive_with_four_functions_and_tests,
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
    return github_mock


@pytest.mark.parametrize('source_code, expected_names', [
    # normal case
    (
            '''
            def add(x, y): 
                x += 1
                return x + y
            ''',
            ['add'],
    ),
    # we ignore functions with bad names
    (
            '''
            def teSt_add(x, y):
                x += 1
                assert x == y
                
            def assErt_equal(x, y):
                x += 1
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
                x += 1
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
            '''def add(x, y): x += 1; return x + y''',
            [],
    ),
    # we ignore functions with too few statements
    (
            '''def add(x, y):
                return (
                    x + y
                )
            ''',
            []
    ),
    # we ignore functions with `raise NotImplementedError` (two spaces after raise are intentional)
    (
            '''def add(x, y):
                x += 1
                raise  NotImplementedError
            ''',
            []
    ),
    # we ignore __init__ (to avoid having a boring function with a bunch of assignments)
    (
            '''def __init__(self, x, y):
                self.x = x
                self.y = y
            ''',
            []
    ),
    # we ignore functions inside of the classes with the test in it
    (
            '''class TestCase(unittest.TestCase):
                    def setUp(self):
                        self.x = x
                        self.y = y
            ''',
            []
    ),
])
def test_select_good_functions(source_code, expected_names, monkeypatch):
    monkeypatch.setattr(loader.Selector, 'MIN_NUM_STATEMENTS', 2)
    functions = parser.get_functions_from_fileobj(
        io.StringIO(textwrap.dedent(source_code)), 'file.py')
    good_functions = loader.select_good_functions(functions)
    actual_names = {a_function.name for a_function in good_functions}
    assert actual_names == set(expected_names)


def _add_data(pymash_engine):
    with pymash_engine.connect() as conn:
        conn.execute(Repos.insert().values({
            # -2 to avoid conflict with postgres auto sequence which starts with 0
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
            Functions.c.file_name: 'flask.py',
            Functions.c.line_number: 100333,
        }))
        conn.execute(Functions.insert().values({
            Functions.c.function_id: 888,
            Functions.c.repo_id: -2,
            Functions.c.text: 'def mul(x, y):\n    return x * y',
            Functions.c.is_active: True,
            Functions.c.random: 0.7,
            Functions.c.file_name: 'flask.py',
            Functions.c.line_number: 100444,
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
            Functions.c.file_name: 'requests.py',
            Functions.c.line_number: 100555,
        }))


def _assert_repo_was_loaded(pymash_engine):
    with pymash_engine.connect() as conn:
        rows = list(conn.execute(Repos.select()))
        django_row = _find_repo_by_id(conn, 1001)
        flask_row = _find_repo_by_id(conn, 1002)
        pymash_row = _find_repo_by_id(conn, 1003)
        requests_row = _find_repo_by_id(conn, 1005)
    assert len(rows) == 4

    _expect_repo(
        repo_row=django_row,
        name='django',
        url='https://github.com/django/django',
        is_active=True,
        rating=models.Repo.DEFAULT_RATING)
    _expect_repo(
        repo_row=flask_row,
        name='flask',
        url='https://github.com/pallets/flask',
        is_active=True,
        rating=1900)
    _expect_repo(
        repo_row=pymash_row,
        name='pymash',
        url='https://github.com/alexandershov/pymash',
        is_active=True,
        rating=1800)
    _expect_repo(
        repo_row=requests_row,
        name='requests',
        url='https://github.com/requests/requests',
        is_active=False,
        rating=2000)


def _expect_repo(repo_row, name, url, is_active, rating):
    repo = db.make_repo_from_db_row(repo_row)
    assert repo.name == name
    assert repo.url == url
    assert repo.is_active is is_active
    assert repo.rating == rating


def _find_repo_by_id(conn, repo_id):
    return conn.execute(Repos.select().where(Repos.c.github_id == repo_id)).first()


def _assert_functions_were_loaded(pymash_engine):
    with pymash_engine.connect() as conn:
        all_rows = list(conn.execute(Functions.select()))
        _assert_grouped_functions(conn, 'django', {
            'def add(x, y):\n    return x + y': True,
            'def sub(x, y):\n    return x - y': True,
        })
        _assert_grouped_functions(conn, 'flask', {
            'def add(x, y):\n    return x + y': True,
            'def sub(x, y):\n    return x - y': True,
            'def mul(x, y):\n    return x * y': False,
        })
        _assert_grouped_functions(conn, 'pymash', {
            'def add(x, y):\n    return x + y': True,
            'def sub(x, y):\n    return x - y': True,
        })
        _assert_grouped_functions(conn, 'requests', {
            'def add(x, y):\n    return x + y': False,
        })
    assert len(all_rows) == 8


def _assert_grouped_functions(conn, repo_name, _grouped_by_text):
    rows = _find_functions_with_repo_name(conn, repo_name)
    assert len(rows) == len(_grouped_by_text)
    functions = list(map(db.make_function_from_db_row, rows))
    assert _group_by_text(functions) == _grouped_by_text


def _find_functions_with_repo_name(conn, repo_name):
    return list(conn.execute(
        Functions.join(Repos, sa.and_(Functions.c.repo_id == Repos.c.repo_id,
                                      Repos.c.name == repo_name)).select()))


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
