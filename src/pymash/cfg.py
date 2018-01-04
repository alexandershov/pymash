import os

import voluptuous as vol


class BaseError(Exception):
    pass


class ConfigError(Exception):
    pass


_ENV_CONFIG_SCHEMA = vol.Schema(
    {
        'PYMASH_DSN': str,
        'PYMASH_GAME_HASH_SALT': str
    },
    required=True, extra=vol.ALLOW_EXTRA)


def get_config():
    try:
        parsed_config = _ENV_CONFIG_SCHEMA(dict(os.environ))
    except vol.Invalid as exc:
        raise ConfigError from exc
    return Config(
        # TODO(aershov182): extract keys to constants
        dsn=parsed_config['PYMASH_DSN'],
        game_hash_salt=parsed_config['PYMASH_GAME_HASH_SALT'])


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
