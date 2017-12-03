from aiohttp import web
from pymash import views


def setup_routes(app: web.Application):
    app.router.add_get('/game', views.show_game)
