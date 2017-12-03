from aiohttp import web


def show_game(request: web.Request) -> web.Response:
    return web.Response(text='hello!')
