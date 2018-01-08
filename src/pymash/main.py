import argparse

import aioboto3
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
    config = cfg.get_config()
    app['config'] = config
    app.on_startup.append(_create_engine)
    app.on_startup.append(_create_sqs_resource)
    app.on_cleanup.append(_close_engine)
    app.on_cleanup.append(_close_sqs_resource)
    routes.setup_routes(app)
    aiohttp_jinja2.setup(
        app, loader=jinja2.PackageLoader('pymash', 'templates')
    )
    return app


async def _create_engine(app):
    app['db_engine'] = await sa.create_engine(app['config'].dsn, loop=app.loop)


async def _create_sqs_resource(app):
    config = app['config']
    app['sqs_resource'] = aioboto3.resource(
        'sqs',
        loop=app.loop,
        region_name=config.aws_region_name,
        aws_access_key_id=config.aws_access_key_id,
        aws_secret_access_key=config.aws_secret_access_key)


async def _close_engine(app):
    app['db_engine'].close()
    await app['db_engine'].wait_closed()


async def _close_sqs_resource(app):
    await app['sqs_resource'].close()


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default='8000')
    return parser.parse_args()


if __name__ == '__main__':
    main()
