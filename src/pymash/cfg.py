import os


class BaseError(Exception):
    pass


class ConfigError(Exception):
    pass


def get_config():
    # TODO(aershov182): maybe use voluptuous for parsing?
    return Config(
        dsn=_get_env('PYMASH_DSN', str),
        game_hash_salt=_get_env('PYMASH_GAME_HASH_SALT', str))


class Config:
    def __init__(self, dsn: str, game_hash_salt: str):
        self.dsn = dsn
        self.game_hash_salt = game_hash_salt


def _get_env(name, parser):
    if name not in os.environ:
        raise ConfigError(f'environment variable {name} is not defined!')
    str_value = os.environ[name]
    try:
        return parser(str_value)
    except ValueError:
        raise ConfigError(f'{name} is not a valid {parser.__name__}')
