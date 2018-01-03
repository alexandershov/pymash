import aiohttp_jinja2
from aiohttp import web

from pymash import db


@aiohttp_jinja2.template('leaders.html')
async def show_leaders(request: web.Request) -> dict:
    repos = await db.find_repos_order_by_rating(request.app['db_engine'])
    return {
        'repos': repos,
    }


async def show_game(request: web.Request) -> web.Response:
    return web.Response(text='hello!')
