import hashlib

import aiohttp_jinja2
import voluptuous as vol
from aiohttp import web

from pymash import db
from pymash import events


# TODO(aershov182): shouldn't it live in the models?
class Game:
    def __init__(self, game_id, white_id, white_score, black_id, black_score):
        self.game_id = game_id
        self.white_id = white_id
        self.white_score = white_score
        self.black_id = black_id
        self.black_score = black_score


@aiohttp_jinja2.template('leaders.html')
async def show_leaders(request: web.Request) -> dict:
    repos = await db.find_repos_order_by_rating(request.app['db_engine'])
    return {
        'repos': repos,
    }


_VALID_ID = vol.And(str, vol.Coerce(int))

_VALID_SCORE = vol.And(str, vol.Coerce(int), vol.In([0, 1]))

_POST_GAME_INPUT_SCHEMA = vol.Schema(
    {
        'white_id': _VALID_ID,
        'black_id': _VALID_ID,
        'white_score': _VALID_SCORE,
        'black_score': _VALID_SCORE,
        'hash': str,
    },
    required=True, extra=vol.ALLOW_EXTRA)


async def post_game(request: web.Request) -> web.Response:
    data = await request.post()
    game_id = request.match_info['game_id']
    try:
        parsed_input = _POST_GAME_INPUT_SCHEMA(dict(data))
    except vol.Invalid as exc:
        # TODO(aershov182): logging
        print(exc)
        return web.HTTPBadRequest()
    game = Game(
        game_id=game_id,
        white_id=parsed_input['white_id'],
        white_score=parsed_input['white_score'],
        black_id=parsed_input['black_id'],
        black_score=parsed_input['black_score'],
    )
    if game.white_score + game.black_score != 1:
        return web.HTTPBadRequest()
    expected_hash = calc_game_hash(game, request.app['config'].game_hash_salt)
    if expected_hash != data['hash']:
        return web.HTTPBadRequest()
    await events.post_game_finished_event(
        game_id=game.game_id,
        white_id=game.white_id,
        black_id=game.black_id,
        white_score=game.white_score,
        black_score=game.black_score)
    redirect_url = request.app.router['new_game'].url_for()
    return web.HTTPFound(redirect_url)


async def show_game(request: web.Request) -> web.Response:
    return web.Response(text='hello!')


def calc_game_hash(game: Game, salt: str) -> str:
    s = ':'.join([game.game_id, salt])
    return hashlib.sha1(s.encode('utf-8')).hexdigest()
