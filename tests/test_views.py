import urllib.parse as urlparse

import pytest
import sqlalchemy as sa

from pymash import cfg
from pymash import main
from pymash import tables


@pytest.fixture(scope='session')
def _system_engine(request):
    return _get_engine(request, 'postgres')


@pytest.fixture(scope='session')
def _pymash_engine(request):
    return _get_engine(request)


def _get_engine(request, database=None):
    config = cfg.get_config()
    if database is not None:
        dsn = _replace_dsn_database(config.dsn, database)
    else:
        dsn = config.dsn
    engine = sa.create_engine(dsn)
    request.addfinalizer(engine.dispose)
    return engine


def _replace_dsn_database(dsn, new_database):
    parsed = urlparse.urlparse(dsn)
    replaced = parsed._replace(path=new_database)
    return replaced.geturl()


@pytest.fixture(scope='session', autouse=True)
def _create_database(request, _system_engine):
    test_db_name = _get_test_db_name()
    # TODO(aershov182): use sqlalchemy for query generation
    with _system_engine.connect().execution_options(
            isolation_level="AUTOCOMMIT") as conn:
        conn.execute(f'DROP DATABASE IF EXISTS {test_db_name}')
        conn.execute(f'CREATE DATABASE {test_db_name}')
    create_tables()
    request.addfinalizer(lambda: _drop_database(_system_engine))


def _drop_database(system_engine):
    # TODO(aershov182): remove duplication with _create_database
    test_db_name = _get_test_db_name()
    # TODO(aershov182): use sqlalchemy for query generation
    with system_engine.connect().execution_options(
            isolation_level="AUTOCOMMIT") as conn:
        conn.execute(f'DROP DATABASE {test_db_name}')


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
    tables.Base.metadata.create_all(engine)
    # TODO(aershov182): maybe use context manager to dispose
    engine.dispose()


async def _clean_tables(app):
    async with app['db_engine'].acquire() as conn:
        for sa_model in tables.Base.__subclasses__():
            table = sa_model.__table__
            conn.execute(table.delete())
