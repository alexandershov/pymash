import os

from aiohttp import web

from pymash import views


def setup_routes(app: web.Application):
    app.router.add_get('/', views.show_game, name='new_game')
    app.router.add_get('/game', views.show_game, name='new_game')

    app.router.add_post('/game/{game_id}', views.post_game, name='post_game')

    app.router.add_get('/leaders', views.show_leaders, name='show_leaders')

    app.router.add_static(
        '/static', os.path.join(os.path.dirname(__file__), 'templates', 'static'))
