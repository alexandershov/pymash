import argparse
import os

from aiohttp import web
from aiopg import sa

from pymash import routes


class ConfigError(Exception):
    pass


class Config:
    def __init__(self, dsn: str):
        self.dsn = dsn


def main():
    app = create_app()
    args = _parse_args()
    web.run_app(app, host=args.host, port=args.port)


def create_app() -> web.Application:
    app = web.Application()
    set_config(app)
    app.on_startup.append(_create_engine)
    app.on_cleanup.append(_close_engine)
    routes.setup_routes(app)
    return app


# TODO(aershov182): move to different module
def set_config(app):
    app['config'] = get_config()


def get_config():
    return Config(
        dsn=_get_env('PYMASH_DSN', str),
    )


def _get_env(name, parser):
    if name not in os.environ:
        raise ConfigError(f'environment variable {name} is not defined!')
    str_value = os.environ[name]
    try:
        return parser(str_value)
    except ValueError:
        raise ConfigError(f'{name} is not a valid {parser.__name__}')


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
