import argparse
import os

from aiohttp import web

from pymash import routes


class ConfigError(Exception):
    pass


class DbConfig:
    def __init__(self, user, password, name, host, port):
        self.user = user
        self.password = password
        self.name = name
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
    routes.setup_routes(app)
    return app


# TODO(aershov182): move to different module
def set_config(app):
    db_config = _read_db_config()
    app['config'] = Config(db_config)


def _read_db_config():
    return DbConfig(
        user=_get_env('PYMASH_DB_USER', str),
        password=_get_env('PYMASH_DB_PASSWORD', str),
        name=_get_env('PYMASH_DB_NAME', str),
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


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default='8000')
    return parser.parse_args()


if __name__ == '__main__':
    main()
