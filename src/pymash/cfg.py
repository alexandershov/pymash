import os


class BaseError(Exception):
    pass


class ConfigError(Exception):
    pass


def get_config():
    return Config(
        dsn=_get_env('PYMASH_DSN', str),
    )


class Config:
    def __init__(self, dsn: str):
        self.dsn = dsn


def _get_env(name, parser):
    if name not in os.environ:
        raise ConfigError(f'environment variable {name} is not defined!')
    str_value = os.environ[name]
    try:
        return parser(str_value)
    except ValueError:
        raise ConfigError(f'{name} is not a valid {parser.__name__}')
