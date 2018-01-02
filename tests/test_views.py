import psycopg2
import sqlalchemy as sa
import pytest

import urllib.parse as urlparse

from pymash import cfg
from pymash import main
from pymash import tables


@pytest.fixture(scope='session', autouse=True)
def _create_database(request):
    cursor = _get_sync_main_cursor()
    test_database = _get_db_name()
    # TODO(aershov182): use sqlalchemy for query generation
    cursor.execute(f'DROP DATABASE IF EXISTS {test_database}')
    cursor.execute(f'CREATE DATABASE {test_database}')
    create_tables()
    request.addfinalizer(_drop_database)


# TODO(aershov182): is it possible to do async connection here?
def _get_sync_main_cursor():
    config = cfg.get_config()
    parsed = urlparse.urlparse(config.dsn)
    postgres_parsed = parsed._replace(path='postgres')
    # TODO(aershov182): close connection
    connection = psycopg2.connect(postgres_parsed.geturl())
    cursor = connection.cursor()
    cursor.execute('end;')
    return cursor


def _get_db_name():
    config = cfg.get_config()
    return urlparse.urlparse(config.dsn).path.lstrip('/')


def _drop_database():
    # TODO(aershov182): remove duplication with _create_database
    test_database = _get_db_name()
    connection = _get_sync_main_cursor()
    # TODO(aershov182): use sqlalchemy for query generation
    connection.execute(f'DROP DATABASE {test_database}')


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
