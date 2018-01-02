import pytest

import psycopg2
from pymash import main


@pytest.fixture(scope='session', autouse=True)
def _create_database(request):
    db_config = main._read_db_config()
    test_database = db_config.database
    cursor = _get_sync_main_cursor()
    # TODO(aershov182): use sqlalchemy for query generation
    cursor.execute(f'CREATE DATABASE {test_database}')
    request.addfinalizer(_drop_database)


# TODO(aershov182): is it possible to do async connection here?
def _get_sync_main_cursor():
    db_config = main._read_db_config()
    db_config.database = 'postgres'
    # TODO(aershov182): close connection
    connection = psycopg2.connect(
        user=db_config.user,
        password=db_config.password,
        database=db_config.database,
        host=db_config.host,
        port=db_config.port,
    )
    cursor = connection.cursor()
    cursor.execute('end;')
    return cursor


def _drop_database():
    # TODO(aershov182): remove duplication with _create_database
    db_config = main._read_db_config()
    test_database = db_config.database
    connection = _get_sync_main_cursor()
    # TODO(aershov182): use sqlalchemy for query generation
    connection.execute(f'DROP DATABASE {test_database}')


async def test_get_game(test_client):
    text = await _get(test_client, '/game')
    assert text == 'hello!'


async def _get(test_client, path):
    app = main.create_app()
    client = await test_client(app)
    resp = await client.get(path)
    text = await resp.text()
    return text
