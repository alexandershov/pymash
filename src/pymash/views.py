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
    await events.post_game_finished_event(0, 0, 0, 1, 0)
    return web.Response(text='{}')


async def show_game(request: web.Request) -> web.Response:
    return web.Response(text='hello!')
