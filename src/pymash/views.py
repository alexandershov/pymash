import decimal

import aiohttp_jinja2
from aiohttp import web

from pymash import db
from pymash import events


@aiohttp_jinja2.template('leaders.html')
async def show_leaders(request: web.Request) -> dict:
    repos = await db.find_repos_order_by_rating(request.app['db_engine'])
    return {
        'repos': repos,
    }


async def post_game(request: web.Request) -> web.Response:
    data = await request.post()
    game_id = request.match_info['game_id']
    try:
        white_score = int(data['white_score'])
        black_score = int(data['black_score'])
    except ValueError:
        return web.HTTPBadRequest()
    if white_score not in [0, 1] or black_score not in [0, 1] or white_score + black_score != 1:
        return web.HTTPBadRequest()
    await events.post_game_finished_event(
        game_id=game_id,
        white_id=int(data['white_id']),
        black_id=int(data['black_id']),
        white_score=white_score,
        black_score=black_score)
    return web.Response(text='{}')


async def show_game(request: web.Request) -> web.Response:
    return web.Response(text='hello!')
