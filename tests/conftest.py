import string
import urllib.parse as urlparse

import pytest
import sqlalchemy as sa

from pymash import cfg
from pymash import tables


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