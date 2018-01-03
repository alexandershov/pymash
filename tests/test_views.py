import string
import urllib.parse as urlparse

import pytest
import sqlalchemy as sa

from pymash import cfg
from pymash import main
from pymash import tables


@pytest.fixture(scope='session')
def system_engine(request):
    return _get_engine(request, 'postgres')


@pytest.fixture(scope='session')
def pymash_engine(request):
    return _get_engine(request)


def _get_engine(request, database=None):
    config = cfg.get_config()
    if database is not None:
        dsn = _replace_database_in_dsn(config.dsn, database)
    else:
        dsn = config.dsn
    engine = sa.create_engine(dsn)
    request.addfinalizer(engine.dispose)
    return engine


def _replace_database_in_dsn(dsn, new_database):
    parsed = urlparse.urlparse(dsn)
    replaced = parsed._replace(path=new_database)
    return replaced.geturl()


@pytest.fixture(scope='session', autouse=True)
def _create_database(request, system_engine):
    test_db_name = _get_test_db_name()
    _run_system_commands(
        system_engine,
        _drop_db_stmt(test_db_name), _create_db_stmt(test_db_name))
    create_tables()
    request.addfinalizer(lambda: _drop_database(test_db_name, system_engine))


def _drop_database(db_name, system_engine):
    _run_system_commands(
        system_engine,
        _drop_db_stmt(db_name))


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


async def test_show_game(test_client):
    text = await _get(test_client, '/game')
    assert text == 'hello!'


async def test_show_leaders(test_client):
    text = await _get(test_client, '/leaders')
    assert text == '0'


async def _get(test_client, path):
    app = main.create_app()
    # TODO(aershov182): adding to on_startup should be more visible
    app.on_startup.append(_clean_tables)
    client = await test_client(app)
    resp = await client.get(path)
    text = await resp.text()
    return text


def create_tables():
    config = cfg.get_config()
    engine = sa.create_engine(config.dsn)
    # TODO(aershov182): use pymash_engine fixture
    tables.Base.metadata.create_all(engine)
    engine.dispose()


async def _clean_tables(app):
    async with app['db_engine'].acquire() as conn:
        for sa_model in tables.Base.__subclasses__():
            table = sa_model.__table__
            conn.execute(table.delete())
