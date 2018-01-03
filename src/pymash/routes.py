from aiohttp import web
from pymash import views


def setup_routes(app: web.Application):
    app.router.add_get('/game', views.show_game)
    app.router.add_post('/game/{game_id}', views.post_game)
    app.router.add_get('/leaders', views.show_leaders)
