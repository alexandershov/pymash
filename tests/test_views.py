import random
import string
import urllib.parse as urlparse

import pytest
import sqlalchemy as sa
from aiohttp import web

from pymash import cfg
from pymash import events
from pymash import main
from pymash import tables
from pymash.tables import Repos


async def test_show_game(test_client):
    app = _create_app()
    text = await _get_text(app, test_client, '/game')
    assert text == 'hello!'


async def test_show_leaders(test_client):
    app = _create_app()
    app.on_startup.append(_add_repos_for_test_show_leaders)
    # TODO(aershov182): change assertions when we'll have a real markup
    text = await _get_text(app, test_client, '/leaders')
    flask_index = text.index('1901')
    django_index = text.index('1801')
    assert flask_index < django_index


@pytest.mark.parametrize('data, expected_status, expected_num_calls', [
    # normal case
    (
            {
                'white_id': 905,
                'black_id': 1005,
                'white_score': 1,
                'black_score': 0,
                'hash': 'some_game_hash',
            },
            200,
            1,
    ),
    # bad white score
    (
            {
                'white_id': 905,
                'black_id': 1005,
                'white_score': 2,
                'black_score': 0,
                'hash': 'some_game_hash',
            },
            400,
            0,
    ),
    # bad black score
    (
            {
                'white_id': 905,
                'black_id': 1005,
                'white_score': 0,
                'black_score': 2,
                'hash': 'some_game_hash',
            },
            400,
            0,
    ),
    # bad black&white score score
    (
            {
                'white_id': 905,
                'black_id': 1005,
                'white_score': 1,
                'black_score': 1,
                'hash': 'some_game_hash',
            },
            400,
            0,
    )
])
async def test_post_game(data, expected_status, expected_num_calls, test_client, monkeypatch):
    num_calls = 0

    async def post_game_finished_event(game_id, white_id, black_id, white_score, black_score):
        nonlocal num_calls
        num_calls += 1

    monkeypatch.setattr(events, 'post_game_finished_event', post_game_finished_event)
    app = _create_app()
    response = await _post(app, test_client, '/game/some_game_id', data=data)
    assert response.status == expected_status
    # TODO(aershov182): check response text
    assert num_calls == expected_num_calls


async def _add_repos_for_test_show_leaders(app):
    await _add_some_repo_with_rating(app, 1801)
    await _add_some_repo_with_rating(app, 1901)


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
    _create_tables()
    request.addfinalizer(lambda: _drop_database(test_db_name, system_engine))


def _create_tables():
    config = cfg.get_config()
    engine = sa.create_engine(config.dsn)
    # TODO(aershov182): use pymash_engine fixture
    tables.Base.metadata.create_all(engine)
    engine.dispose()


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


async def _get_text(app, test_client, path) -> str:
    client = await test_client(app)
    resp = await client.get(path)
    return await _get_checked_response_text(resp)


async def _post_text(app, test_client, path, data=None) -> str:
    resp = await _post(app, test_client, path, data=data)
    return await _get_checked_response_text(resp)


async def _post(app, test_client, path, data=None) -> web.Response:
    client = await test_client(app)
    return await client.post(path, data=data)


async def _get_checked_response_text(resp):
    text = await resp.text()
    resp.raise_for_status()
    return text


def _create_app():
    app = main.create_app()
    app.on_startup.append(_clean_tables)
    return app


async def _clean_tables(app):
    async with app['db_engine'].acquire() as conn:
        for sa_model in tables.Base.__subclasses__():
            table = sa_model.__table__
            await conn.execute(table.delete())


async def _add_some_repo_with_rating(app, rating):
    name = 'some_repo_name_' + str(random.randint(1, 1000))
    url = f'https://github.com/org/{name}'
    async with app['db_engine'].acquire() as conn:
        await conn.execute(Repos.insert().values(
            name=name,
            url=url,
            rating=rating))
