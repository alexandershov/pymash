import asyncio
import collections
import json
import random
from unittest import mock

import aiohttp
import bs4
import pytest

from pymash import cfg
from pymash import main
from pymash import models
from pymash.tables import *


@pytest.mark.parametrize('random_values, cookies, is_success', [
    # normal case, first visit
    ([0.3, 0.6], {}, True),
    # normal case, second visit
    ([0.3, 0.6], {'visited': '1'}, True),
    # we don't select deactivated functions (function_id=888)
    ([0.3, 0.5], {}, True),
    # if random value is too large, then we cut it to the largest possible value in the database
    ([0.3, 0.9999], {}, True),
    # first game is with the same repo, second is ok
    ([0.3, 0.3, 0.3, 0.6], {}, True),
    # first two games are with the same repo, third is ok
    ([0.3, 0.3, 0.3, 0.3, 0.3, 0.6], {}, True),
    # three games are with the same repo - we return 500 in this case
    # (this has a change of happening ~ 1e-9 on production data)
    ([0.3, 0.3, 0.3, 0.3, 0.3, 0.3], {}, False),
])
@pytest.mark.usefixtures('add_functions_and_repos')
async def test_show_game(random_values, cookies, is_success, test_client, monkeypatch):
    values = collections.deque(random_values)

    def stateful_random():
        return values.popleft()

    monkeypatch.setattr(random, 'random', stateful_random)
    app = main.create_app()
    response = await _get(app, test_client, '/game', cookies=cookies)
    if is_success:
        text = await _get_checked_response_text(response)
        _check_game_markup(text, cookies)
        assert 'visited' in response.cookies
    else:
        assert response.status == 503


async def test_show_leaders(pymash_engine, test_client):
    app = main.create_app()
    _add_repos_for_test_show_leaders(pymash_engine)
    text = await _get_text(app, test_client, '/leaders')
    assert _parse_leaders_ratings(text) == [1901, 1801]


def _parse_leaders_ratings(html_text):
    parsed_html = bs4.BeautifulSoup(html_text)
    rating_cells = parsed_html.find_all('td', attrs={'class': 'rating-column'})
    return [
        int(cell.text)
        for cell in rating_cells
    ]


def _check_game_markup(html_text, cookies):
    parsed_html = bs4.BeautifulSoup(html_text)
    django_data = _get_game_form_data(parsed_html.find('div', attrs={'class': 'white-player'}))
    flask_data = _get_game_form_data(parsed_html.find('div', attrs={'class': 'black-player'}))
    assert django_data == _GameFormData(
        white_id='666',
        black_id='777',
        white_score=1,
        black_score=0)
    assert flask_data == _GameFormData(
        white_id='666',
        black_id='777',
        white_score=0,
        black_score=1)
    choose_buttons = parsed_html.find_all('button', attrs={'class': 'choose'})
    if 'visited' in cookies:
        expected_button_text = 'Choose'
    else:
        expected_button_text = 'This code is better!'
    for button in choose_buttons:
        assert button.text.strip() == expected_button_text


_GameFormData = collections.namedtuple(
    '_GameFormData', [
        'white_id',
        'black_id',
        'white_score',
        'black_score',
    ]
)


def _get_game_form_data(player_html_element):
    return _GameFormData(
        white_id=_get_input_value(player_html_element, 'white_id'),
        black_id=_get_input_value(player_html_element, 'black_id'),
        white_score=int(_get_input_value(player_html_element, 'white_score')),
        black_score=int(_get_input_value(player_html_element, 'black_score')))


def _get_input_value(ancestor_html_element, name):
    return ancestor_html_element.find('input', attrs={'name': name})['value']


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
    app = main.create_app()
    games_queue_mock = await _monkeypatch_sqs(app, monkeypatch)
    x_forwarded_for_header = '192.168.1.1, 127.0.0.1'
    response = await _post(app, test_client, '/game/some_game_id',
                           allow_redirects=False,
                           data=data,
                           headers={'X-Forwarded-For': x_forwarded_for_header})
    if is_success:
        assert response.status == 302
        assert response.headers['Location'] == '/game'
        calls = games_queue_mock.send_message.mock_calls
        assert len(calls) == 1
        _, _, call_kwargs = calls[0]
        assert json.loads(call_kwargs['MessageBody'])['ip'] == '192.168.1.1'
    else:
        assert response.status == 400
        games_queue_mock.send_message.assert_not_called()


async def _monkeypatch_sqs(app, monkeypatch):
    sqs_resource_mock = _sqs_resource_mock()
    games_queue_mock = await sqs_resource_mock.get_queue_by_name('some_name')
    app.on_startup.append(_SqsAppMock(monkeypatch, sqs_resource_mock))
    return games_queue_mock


class _SqsAppMock:
    def __init__(self, monkeypatch, sqs_resource_mock):
        self._monkeypatch = monkeypatch
        self._sqs_resource_mock = sqs_resource_mock

    async def __call__(self, app):
        # close real sqs_resource to avoid "Unclosed client session" errors
        await app['sqs_resource'].close()
        self._monkeypatch.setitem(app, 'sqs_resource', self._sqs_resource_mock)


def _sqs_resource_mock():
    games_queue_mock = mock.Mock()
    games_queue_mock.send_message.return_value = _make_future_with_result(None)
    sqs_resource_mock = mock.Mock()
    sqs_resource_mock.get_queue_by_name.return_value = _make_future_with_result(games_queue_mock)
    sqs_resource_mock.close.return_value = _make_future_with_result(None)
    return sqs_resource_mock


def _make_future_with_result(result):
    future = asyncio.Future()
    future.set_result(result)
    return future


def _add_repos_for_test_show_leaders(pymash_engine):
    _add_some_repo_with_rating(pymash_engine, github_id=1001, rating=1801, is_active=True)
    _add_some_repo_with_rating(pymash_engine, github_id=1002, rating=1901, is_active=True)
    _add_some_repo_with_rating(pymash_engine, github_id=1003, rating=2001, is_active=False)


async def _get_text(app, test_client, path) -> str:
    resp = await _get(app, test_client, path)
    return await _get_checked_response_text(resp)


async def _get(app, test_client, path, cookies=None) -> aiohttp.client.ClientResponse:
    client = await test_client(app, cookies=cookies)
    return await client.get(path)


async def _post_text(app, test_client, path, data=None) -> str:
    resp = await _post(app, test_client, path, data=data)
    return await _get_checked_response_text(resp)


async def _post(app, test_client, path, allow_redirects=True,
                data=None, headers=None) -> aiohttp.client.ClientResponse:
    client = await test_client(app)
    return await client.post(
        path,
        allow_redirects=allow_redirects,
        data=data,
        headers=headers)


async def _get_checked_response_text(resp):
    text = await resp.text()
    resp.raise_for_status()
    return text


def _add_some_repo_with_rating(pymash_engine, github_id, rating, is_active):
    name = 'some_repo_name_' + str(github_id)
    url = f'https://github.com/org/{name}'
    with pymash_engine.connect() as conn:
        conn.execute(Repos.insert().values({
            Repos.c.name: name,
            Repos.c.github_id: github_id,
            Repos.c.url: url,
            Repos.c.is_active: is_active,
            Repos.c.rating: rating,
        }))
