import hashlib

import aiohttp_jinja2
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


# TODO(aershov182): use some library for dictionary validation & parsing
async def post_game(request: web.Request) -> web.Response:
    data = await request.post()
    if set(data) != {'white_id', 'black_id', 'white_score', 'black_score', 'hash'}:
        return web.HTTPBadRequest()
    game_id = request.match_info['game_id']
    try:
        white_score = int(data['white_score'])
        black_score = int(data['black_score'])
    except ValueError:
        return web.HTTPBadRequest()
    if white_score not in [0, 1] or black_score not in [0, 1] or white_score + black_score != 1:
        return web.HTTPBadRequest()
    try:
        white_id = int(data['white_id'])
        black_id = int(data['black_id'])
    except ValueError:
        return web.HTTPBadRequest()
    game = Game(
        game_id=game_id,
        white_id=white_id,
        white_score=white_score,
        black_id=black_id,
        black_score=black_score,
    )
    expected_hash = calc_game_hash(game, request.app['config'].game_hash_salt)
    if expected_hash != data['hash']:
        return web.HTTPBadRequest()
    await events.post_game_finished_event(
        game_id=game_id,
        white_id=white_id,
        black_id=black_id,
        white_score=white_score,
        black_score=black_score)
    redirect_url = request.app.router['new_game'].url_for()
    return web.HTTPFound(redirect_url)


async def show_game(request: web.Request) -> web.Response:
    return web.Response(text='hello!')


def calc_game_hash(game: Game, salt: str) -> str:
    s = ':'.join([game.game_id, salt])
    return hashlib.sha1(s.encode('utf-8')).hexdigest()
