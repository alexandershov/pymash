import functools
import time
import uuid

import aiohttp_jinja2
import voluptuous as vol
from aiohttp import web

from pymash import db
from pymash import events
from pymash import loggers
from pymash import models
from pymash import type_aliases as ta
from pymash import utils

_CACHE_LEADERS_IN_SECONDS = 5


def _cache_coroutine_by_time(seconds):
    def decorator(view):
        cache = {}

        async def cached_view(*args, **kwargs):
            now = _floor_to_full_nearest_multiply(int(time.time()), seconds)
            if now not in cache:
                loggers.web.info('%s cache miss', view.__name__)
                cache.clear()
                result = await view(*args, **kwargs)
                cache[now] = result
            else:
                loggers.web.info('%s cache hit', view.__name__)
            return cache[now]

        return functools.update_wrapper(cached_view, view)

    return decorator


@utils.log_time(loggers.web)
@aiohttp_jinja2.template('leaders.html')
async def show_leaders(request: web.Request) -> ta.DictOrResponse:
    repos = await _cached_find_active_repos(request)
    return {
        'repos': repos,
    }


@_cache_coroutine_by_time(_CACHE_LEADERS_IN_SECONDS)
async def _cached_find_active_repos(request):
    repos = await db.find_active_repos_order_by_rating(request.app['db_engine'])
    return repos


class _PostGameInput:
    valid_id = vol.And(str, vol.Coerce(int))
    valid_score = vol.And(str, vol.Coerce(int))

    class Keys:
        white_id = 'white_id'
        black_id = 'black_id'
        white_score = 'white_score'
        black_score = 'black_score'
        hash_ = 'hash'

    schema = vol.Schema(
        {
            Keys.white_id: valid_id,
            Keys.black_id: valid_id,
            Keys.white_score: valid_score,
            Keys.black_score: valid_score,
            Keys.hash_: str,
        },
        required=True, extra=vol.ALLOW_EXTRA)


@utils.log_time(loggers.web)
async def post_game(request: web.Request) -> web.Response:
    data = await request.post()
    game = await _get_game_or_error(request, data)
    _validate_hash(request, game, data[_PostGameInput.Keys.hash_])
    await events.post_game_finished_event(request, game)
    redirect_url = request.app.router['new_game'].url_for()
    return web.HTTPFound(redirect_url)


async def _get_game_or_error(request, data) -> models.Game:
    try:
        parsed_input = _PostGameInput.schema(dict(data))
    except vol.Invalid:
        loggers.web.info('bad request for post_game', exc_info=True)
        raise web.HTTPBadRequest
    keys = _PostGameInput.Keys
    try:
        result = models.GameResult(
            white_score=parsed_input[keys.white_score],
            black_score=parsed_input[keys.black_score])
        return models.Game(
            game_id=request.match_info['game_id'],
            white_id=parsed_input[keys.white_id],
            black_id=parsed_input[keys.black_id],
            result=result)
    except (models.ResultError, models.GameError):
        loggers.web.info('bad request for post_game', exc_info=True)
        raise web.HTTPBadRequest


def _validate_hash(request: web.Request, game: models.Game, actual_hash: str):
    expected_hash = game.get_hash(request.app['config'].game_hash_salt)
    if expected_hash != actual_hash:
        raise web.HTTPBadRequest


@utils.log_time(loggers.web)
@aiohttp_jinja2.template('game.html')
async def show_game(request: web.Request) -> ta.DictOrResponse:
    white, black = await _find_two_random_function_or_error(request.app['db_engine'])
    game = models.Game(
        game_id=uuid.uuid4().hex,
        white_id=white.function_id,
        black_id=black.function_id,
        result=models.UNKNOWN_RESULT)
    return {
        'game': game,
        'white': white,
        'black': black,
    }


async def _find_two_random_function_or_error(engine: ta.AsyncEngine):
    num_tries = 3
    for _ in range(num_tries):
        functions = await db.try_to_find_two_random_functions(engine)
        if _are_valid_functions(functions):
            return functions
    else:
        raise web.HTTPServiceUnavailable


def _are_valid_functions(functions: ta.Functions):
    if len(functions) != 2:
        return False
    white, black = functions
    if white.repo_id == black.repo_id:
        return False
    return True


def _floor_to_full_nearest_multiply(x, n):
    return (x // n) * n
