import argparse

import aioboto3
from aiohttp import web
from aiopg import sa

from pymash import appenv
from pymash import cfg
from pymash import loggers
from pymash import routes
from pymash import utils

ACCESS_LOG_FORMAT = '%t %a %{X-Forwarded-For}i "%r" %s %b %Tf "%{Referer}i" "%{User-Agent}i'


def main():
    args = _parse_args()
    app = create_app()
    web.run_app(
        app,
        host=args.host,
        port=args.port,
        access_log_format=ACCESS_LOG_FORMAT)


def create_app() -> web.Application:
    app = web.Application()
    app['config'] = cfg.get_config()
    _setup_startup_cleanup(app)
    routes.setup_routes(app)
    appenv.setup_jinja2(app)
    return app


def _setup_startup_cleanup(app: web.Application) -> None:
    app.on_startup.append(_setup_logging)
    app.on_startup.append(_create_engine)
    app.on_startup.append(_create_sqs_resource)
    app.on_cleanup.append(_close_engine)
    app.on_cleanup.append(_close_sqs_resource)


# noinspection PyUnusedLocal
async def _setup_logging(app: web.Application) -> None:
    loggers.setup_logging()


@utils.log_time(loggers.web)
async def _create_engine(app: web.Application) -> None:
    app['db_engine'] = await sa.create_engine(app['config'].dsn, loop=app.loop)


@utils.log_time(loggers.web)
async def _close_engine(app: web.Application) -> None:
    app['db_engine'].close()
    await app['db_engine'].wait_closed()


@utils.log_time(loggers.web)
async def _create_sqs_resource(app: web.Application) -> None:
    config = app['config']
    app['sqs_resource'] = aioboto3.resource(
        'sqs',
        loop=app.loop,
        region_name=config.aws_region_name,
        aws_access_key_id=config.aws_access_key_id,
        aws_secret_access_key=config.aws_secret_access_key)


@utils.log_time(loggers.web)
async def _close_sqs_resource(app: web.Application) -> None:
    await app['sqs_resource'].close()


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default='8000')
    return parser.parse_args()


if __name__ == '__main__':
    main()
