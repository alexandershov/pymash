from aiohttp import web

from pymash import db
from pymash import tables


async def show_game(request: web.Request) -> web.Response:
    return web.Response(text='hello!')
    matchup = await db.find_matchup(request.app['connection'])


async def show_leaders(request: web.Request) -> web.Response:
    db_engine = request.app['db_engine']
    num_rows = 0
    async with db_engine.acquire() as conn:
        query = tables.sa_repos.select().order_by(tables.sa_repos.c.score.desc())
        async for row in conn.execute(query):
            num_rows += 1
    return web.Response(text=str(num_rows))
