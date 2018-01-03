from aiohttp import web
import aiohttp_jinja2

from pymash import db
from pymash import tables


async def show_game(request: web.Request) -> web.Response:
    return web.Response(text='hello!')
    matchup = await db.find_matchup(request.app['connection'])


@aiohttp_jinja2.template('leaders.html')
async def show_leaders(request: web.Request) -> dict:
    db_engine = request.app['db_engine']
    rows = []
    async with db_engine.acquire() as conn:
        query = tables.sa_repos.select().order_by(tables.sa_repos.c.score.desc())
        async for a_row in conn.execute(query):
            rows.append(a_row)
    return {
        'repos': rows,
    }
