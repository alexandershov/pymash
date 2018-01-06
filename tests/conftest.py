import string
import urllib.parse as urlparse

import pytest
import sqlalchemy as sa

from pymash import cfg
from pymash import tables
from pymash.tables import *


@pytest.fixture(scope='session')
def system_engine():
    yield from _get_engine('postgres')


@pytest.fixture(scope='session')
def pymash_engine():
    yield from _get_engine()


@pytest.fixture(scope='session', autouse=True)
def _create_database(system_engine, pymash_engine):
    test_db_name = _get_test_db_name()
    _run_system_commands(
        system_engine,
        _drop_db_stmt(test_db_name), _create_db_stmt(test_db_name))
    _create_tables(pymash_engine)
    yield
    pymash_engine.dispose()
    _run_system_commands(
        system_engine,
        _drop_db_stmt(test_db_name))


def _create_tables(pymash_engine):
    tables.Base.metadata.create_all(pymash_engine)


@pytest.fixture(autouse=True)
def clean_tables(pymash_engine):
    with pymash_engine.connect() as conn:
        for table in [Games, Functions, Repos]:
            conn.execute(table.delete())


@pytest.fixture
def add_functions_and_repos(pymash_engine):
    with pymash_engine.connect() as conn:
        conn.execute(Repos.insert().values({
            Repos.c.repo_id: 1,
            Repos.c.name: 'django',
            Repos.c.url: 'https://github.com/django/django',
            Repos.c.rating: 1800,
        }))
        conn.execute(Repos.insert().values({
            Repos.c.repo_id: 2,
            Repos.c.name: 'flask',
            Repos.c.url: 'https://github.com/pallete/flask',
            Repos.c.rating: 1900,
        }))
        conn.execute(Functions.insert().values({
            Functions.c.function_id: 666,
            Functions.c.repo_id: 1,
            Functions.c.text: 'def django(): return 1',
            Functions.c.random: 0.3,
        }))
        conn.execute(Functions.insert().values({
            Functions.c.function_id: 777,
            Functions.c.repo_id: 2,
            Functions.c.text: 'def flask(): return 2',
            Functions.c.random: 0.6,
        }))


def _run_system_commands(system_engine, *commands):
    # we need isolation_level="AUTOCOMMIT", because CREATE/DROP DATABASE can't run in a transaction
    with system_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for a_command in commands:
            conn.execute(a_command)


def _drop_db_stmt(db_name):
    assert _is_valid_db_name(db_name)
    return f'DROP DATABASE IF EXISTS {db_name}'


def _create_db_stmt(db_name):
    assert _is_valid_db_name(db_name)
    return f'CREATE DATABASE {db_name}'


def _is_valid_db_name(db_name):
    allowed_characters = string.ascii_letters + '_'
    return all(c in allowed_characters for c in db_name)


def _get_test_db_name():
    config = cfg.get_config()
    return urlparse.urlparse(config.dsn).path.lstrip('/')


def _get_engine(database=None):
    config = cfg.get_config()
    if database is not None:
        dsn = _replace_database_in_dsn(config.dsn, database)
    else:
        dsn = config.dsn
    engine = sa.create_engine(dsn)
    yield engine
    engine.dispose()


def _replace_database_in_dsn(dsn, new_database):
    parsed = urlparse.urlparse(dsn)
    # noinspection PyProtectedMember
    replaced = parsed._replace(path=new_database)
    return replaced.geturl()
