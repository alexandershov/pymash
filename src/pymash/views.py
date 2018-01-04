import hashlib
import uuid

import aiohttp_jinja2
import voluptuous as vol
from aiohttp import web

from pymash import db
from pymash import events
from pymash import models


@aiohttp_jinja2.template('leaders.html')
async def show_leaders(request: web.Request) -> dict:
    repos = await db.find_repos_order_by_rating(request.app['db_engine'])
    return {
        'repos': repos,
    }


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


async def post_game(request: web.Request) -> web.Response:
    data = await request.post()
    try:
        parsed_input = _PostGameInput.schema(dict(data))
    except vol.Invalid as exc:
        print(exc)
        return web.HTTPBadRequest()
    keys = _PostGameInput.Keys
    try:
        result = models.GameResult(
            white_score=parsed_input[keys.white_score],
            black_score=parsed_input[keys.black_score])
        game = models.Game(
            game_id=request.match_info['game_id'],
            white_id=parsed_input[keys.white_id],
            black_id=parsed_input[keys.black_id],
            result=result)
    except (models.ResultError, models.GameError) as exc:
        print(exc)
        return web.HTTPBadRequest()
    expected_hash = calc_game_hash(game, request.app['config'].game_hash_salt)
    if expected_hash != data[keys.hash_]:
        return web.HTTPBadRequest()
    await events.post_game_finished_event(game)
    redirect_url = request.app.router['new_game'].url_for()
    return web.HTTPFound(redirect_url)


@aiohttp_jinja2.template('game.html')
async def show_game(request: web.Request) -> dict:
    white, black = await db.find_two_random_functions()
    # TODO: check that white & black are from different repos
    game = models.Game(
        game_id=uuid.uuid4().hex,
        white_id=black.function_id,
        black_id=white.function_id,
        result=models.UNKNOWN_RESULT,
    )
    return


def calc_game_hash(game: models.Game, salt: str) -> str:
    # TODO: should also depend on white_id & black_id
    s = ':'.join([game.game_id, salt])
    return hashlib.sha1(s.encode('utf-8')).hexdigest()
