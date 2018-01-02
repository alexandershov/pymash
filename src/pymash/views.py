from aiohttp import web
import aiopg

from pymash import db
from pymash import models


async def show_game(request: web.Request) -> web.Response:
    return web.Response(text='hello!')
    matchup = await db.find_matchup(request.app['connection'])
