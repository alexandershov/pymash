import asyncio
import collections
import random
import string
import urllib.parse as urlparse
from unittest import mock

import aiohttp
import pytest

from pymash import cfg
from pymash import events
from pymash import main
from pymash import models
from pymash import tables
from pymash.tables import *


@pytest.mark.parametrize('random_values, is_success', [
    # normal case
    ([0.3, 0.6], True),
    # if random value is too large, then we cut it to the largest possible value in the database
    # ([0.3, 0.7], True),
    # first game is with the same repo, second is ok
    ([0.3, 0.3, 0.3, 0.6], True),
    # first two games are with the same repo, third is ok
    ([0.3, 0.3, 0.3, 0.3, 0.3, 0.6], True),
    # three games are with the same repo - we return 500 in this case
    # (this has a change of happening ~ 1e-9 on production data)
    ([0.3, 0.3, 0.3, 0.3, 0.3, 0.3], False),
])
async def test_show_game(random_values, is_success, test_client, monkeypatch):
    values = collections.deque(random_values)

    def stateful_random():
        return values.popleft()

    monkeypatch.setattr(random, 'random', stateful_random)
    app = _create_app()
    app.on_startup.append(_add_data_for_test_show_game)
    response = await _get(app, test_client, '/game')
    if is_success:
        text = await _get_checked_response_text(response)
        # TODO(aershov182): change assertions when we'll have a real markup
        assert '666' in text
        assert '777' in text
    else:
        assert response.status == 503


async def test_show_leaders(test_client):
    app = _create_app()
    app.on_startup.append(_add_repos_for_test_show_leaders)
    # TODO(aershov182): change assertions when we'll have a real markup
    text = await _get_text(app, test_client, '/leaders')
    flask_index = text.index('1901')
    django_index = text.index('1801')
    assert flask_index < django_index


async def _add_data_for_test_show_game(app):
    async with app['db_engine'].acquire() as conn:
        await conn.execute(Repos.insert().values(
            repo_id=1,
            name='django',
            url='https://github.com/django/django',
            rating=1800))
        await conn.execute(Repos.insert().values(
            repo_id=2,
            name='flask',
            url='https://github.com/pallete/flask',
            rating=1900))
        await conn.execute(Functions.insert().values(
            function_id=666,
            repo_id=1,
            text='def django(): return 1',
            random=0.3))
        await conn.execute(Functions.insert().values(
            function_id=777,
            repo_id=2,
            text='def flask(): return 2',
            random=0.6))


def _make_post_game_data(white_id='905', black_id='1005', white_score='1', black_score='0',
                         game_hash=None):
    if game_hash is None:
        # noinspection PyTypeChecker
        game = models.Game(
            game_id='some_game_id',
            white_id=white_id,
            black_id=black_id,
            # unknown result because we're only interested in .get_hash() result
            result=models.UNKNOWN_RESULT)
        salt = cfg.get_config().game_hash_salt
        game_hash = game.get_hash(salt)
    return {
        'white_id': white_id,
        'black_id': black_id,
        'white_score': white_score,
        'black_score': black_score,
        'hash': game_hash,
    }


@pytest.mark.parametrize('data, is_success', [
    # normal case
    (_make_post_game_data(), True),
    # bad white score
    (_make_post_game_data(white_score='2'), False),
    # bad black score
    (_make_post_game_data(white_score='0', black_score='2'), False),
    # bad black & white score sum
    (_make_post_game_data(white_score='1', black_score='1'), False),
    # right sum, but wrong individual scores
    (_make_post_game_data(white_score='2', black_score='-1'), False),
    # bad white_id
    (_make_post_game_data(white_id='some_bad_white_id'), False),
    # bad black_id
    (_make_post_game_data(black_id='some_bad_black_id'), False),
    # bad hash
    (_make_post_game_data(game_hash='some_bad_hash'), False),
    # missing white_id key
    ({
         'black_id': '1005',
         'white_score': '1',
         'black_score': '0',
         'hash': 'some_game_hash',
     }, False),
])
async def test_post_game(data, is_success, test_client, monkeypatch):
    post_game_finished_event_mock = mock.Mock(return_value=_make_future_with_result(None))

    monkeypatch.setattr(events, 'post_game_finished_event', post_game_finished_event_mock)
    app = _create_app()
    response = await _post(app, test_client, '/game/some_game_id',
                           allow_redirects=False,
                           data=data)
    if is_success:
        assert response.status == 302
        assert response.headers['Location'] == '/game'
        post_game_finished_event_mock.assert_called_once()
    else:
        assert response.status == 400
        post_game_finished_event_mock.assert_not_called()


def _make_future_with_result(result):
    future = asyncio.Future()
    future.set_result(result)
    return future


async def _add_repos_for_test_show_leaders(app):
    await _add_some_repo_with_rating(app, 1801)
    await _add_some_repo_with_rating(app, 1901)


async def _get_text(app, test_client, path) -> str:
    resp = await _get(app, test_client, path)
    return await _get_checked_response_text(resp)


async def _get(app, test_client, path) -> aiohttp.client.ClientResponse:
    client = await test_client(app)
    return await client.get(path)


async def _post_text(app, test_client, path, data=None) -> str:
    resp = await _post(app, test_client, path, data=data)
    return await _get_checked_response_text(resp)


async def _post(app, test_client, path, allow_redirects=True, data=None) -> aiohttp.client.ClientResponse:
    client = await test_client(app)
    return await client.post(path,
                             allow_redirects=allow_redirects,
                             data=data)


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
        for table in [Games, Functions, Repos]:
            await conn.execute(table.delete())


async def _add_some_repo_with_rating(app, rating):
    name = 'some_repo_name_' + str(random.randint(1, 1000))
    url = f'https://github.com/org/{name}'
    async with app['db_engine'].acquire() as conn:
        await conn.execute(Repos.insert().values(
            name=name,
            url=url,
            rating=rating))
