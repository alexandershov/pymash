import argparse
import os

from aiohttp import web
from aiopg import sa

from pymash import routes


class ConfigError(Exception):
    pass


class DbConfig:
    def __init__(self, user, password, database, host, port):
        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = port


class Config:
    def __init__(self, db: DbConfig):
        self.db = db


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
    db_config = _read_db_config()
    app['config'] = Config(db_config)


def _read_db_config():
    # TODO(aershov182): read just 1 value from environment: DSN:
    # postgres://aershov182:password@localhost:5432/test_pymash
    return DbConfig(
        user=_get_env('PYMASH_DB_USER', str),
        password=_get_env('PYMASH_DB_PASSWORD', str),
        database=_get_env('PYMASH_DB_DATABASE', str),
        host=_get_env('PYMASH_DB_HOST', str),
        port=_get_env('PYMASH_DB_PORT', int),
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
    db_config: DbConfig = app['config'].db
    db_engine = await sa.create_engine(
        user=db_config.user,
        password=db_config.password,
        database=db_config.database,
        host=db_config.host,
        port=db_config.port,
    )
    app['db_engine'] = db_engine


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
