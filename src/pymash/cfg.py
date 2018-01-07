import os

import voluptuous as vol

_PYMASH_GAME_HASH_SALT_ENV_KEY = 'PYMASH_GAME_HASH_SALT'
_PYMASH_DSN_ENV_KEY = 'PYMASH_DSN'
_PYMASH_AWS_REGION = 'PYMASH_AWS_REGION'
_PYMASH_AWS_ACCESS_KEY_ID = 'PYMASH_AWS_ACCESS_KEY_ID'
_PYMASH_AWS_SECRET_ACCESS_KEY = 'PYMASH_AWS_SECRET_ACCESS_KEY'
_PYMASH_SQS_GAMES_QUEUE_NAME = 'PYMASH_SQS_GAMES_QUEUE_NAME'


class BaseError(Exception):
    pass


class ConfigError(BaseError):
    pass


_ENV_CONFIG_SCHEMA = vol.Schema(
    {
        _PYMASH_DSN_ENV_KEY: str,
        _PYMASH_GAME_HASH_SALT_ENV_KEY: str,
        _PYMASH_AWS_REGION: str,
        _PYMASH_AWS_ACCESS_KEY_ID: str,
        _PYMASH_AWS_SECRET_ACCESS_KEY: str,
        _PYMASH_SQS_GAMES_QUEUE_NAME: str,
    },
    required=True, extra=vol.ALLOW_EXTRA)


def get_config():
    try:
        parsed_config = _ENV_CONFIG_SCHEMA(dict(os.environ))
    except vol.Invalid as exc:
        raise ConfigError from exc
    return Config(
        dsn=parsed_config[_PYMASH_DSN_ENV_KEY],
        game_hash_salt=parsed_config[_PYMASH_GAME_HASH_SALT_ENV_KEY],
        aws_region=parsed_config[_PYMASH_AWS_REGION],
        aws_access_key_id=parsed_config[_PYMASH_AWS_ACCESS_KEY_ID],
        aws_secret_access_key=parsed_config[_PYMASH_AWS_SECRET_ACCESS_KEY],
        sqs_games_queue_name=parsed_config[_PYMASH_SQS_GAMES_QUEUE_NAME])


class Config:
    def __init__(self, dsn: str, game_hash_salt: str, aws_region: str, aws_access_key_id: str,
                 aws_secret_access_key: str, sqs_games_queue_name: str):
        self.dsn = dsn
        self.game_hash_salt = game_hash_salt
        self.aws_region = aws_region
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.sqs_games_queue_name = sqs_games_queue_name


def _get_env(name, parser):
    if name not in os.environ:
        raise ConfigError(f'environment variable {name} is not defined!')
    str_value = os.environ[name]
    try:
        return parser(str_value)
    except ValueError:
        raise ConfigError(f'{name} is not a valid {parser.__name__}')
