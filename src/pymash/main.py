import argparse

from aiohttp import web
from aiopg import sa
import aiohttp_jinja2
import jinja2

from pymash import cfg
from pymash import routes


def main():
    app = create_app()
    args = _parse_args()
    web.run_app(app, host=args.host, port=args.port)


def create_app() -> web.Application:
    app = web.Application()
    app['config'] = cfg.get_config()
    app.on_startup.append(_create_engine)
    app.on_cleanup.append(_close_engine)
    routes.setup_routes(app)
    aiohttp_jinja2.setup(
        app, loader=jinja2.PackageLoader('pymash', 'templates')
    )
    return app


async def _create_engine(app):
    app['db_engine'] = await sa.create_engine(app['config'].dsn)


async def _close_engine(app):
    app['db_engine'].close()
    await app['db_engine'].wait_closed()


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default='8000')
    return parser.parse_args()


if __name__ == '__main__':
    main()
