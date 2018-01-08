import os

import voluptuous as vol


class _EnvKey:
    DSN = 'PYMASH_DSN'
    GAME_HASH_SALT = 'PYMASH_GAME_HASH_SALT'
    AWS_REGION_NAME = 'PYMASH_AWS_REGION_NAME'
    AWS_ACCESS_KEY_ID = 'PYMASH_AWS_ACCESS_KEY_ID'
    AWS_SECRET_ACCESS_KEY = 'PYMASH_AWS_SECRET_ACCESS_KEY'
    SQS_GAMES_QUEUE_NAME = 'PYMASH_SQS_GAMES_QUEUE_NAME'
    GITHUB_TOKEN = 'PYMASH_GITHUB_TOKEN'


class BaseError(Exception):
    pass


class ConfigError(BaseError):
    pass


_ENV_CONFIG_SCHEMA = vol.Schema(
    {
        _EnvKey.DSN: vol.Url(),
        _EnvKey.GAME_HASH_SALT: str,
        _EnvKey.AWS_REGION_NAME: str,
        _EnvKey.AWS_ACCESS_KEY_ID: str,
        _EnvKey.AWS_SECRET_ACCESS_KEY: str,
        _EnvKey.SQS_GAMES_QUEUE_NAME: str,
        _EnvKey.GITHUB_TOKEN: str,
    },
    required=True, extra=vol.ALLOW_EXTRA)


class Config:
    def __init__(self, dsn: str, game_hash_salt: str, aws_region_name: str, aws_access_key_id: str,
                 aws_secret_access_key: str, sqs_games_queue_name: str, github_token: str) -> None:
        self.dsn = dsn
        self.game_hash_salt = game_hash_salt
        self.aws_region_name = aws_region_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.sqs_games_queue_name = sqs_games_queue_name
        self.github_token = github_token


def get_config() -> Config:
    try:
        parsed_config = _ENV_CONFIG_SCHEMA(dict(os.environ))
    except vol.Invalid as exc:
        raise ConfigError from exc
    return Config(
        dsn=parsed_config[_EnvKey.DSN],
        game_hash_salt=parsed_config[_EnvKey.GAME_HASH_SALT],
        aws_region_name=parsed_config[_EnvKey.AWS_REGION_NAME],
        aws_access_key_id=parsed_config[_EnvKey.AWS_ACCESS_KEY_ID],
        aws_secret_access_key=parsed_config[_EnvKey.AWS_SECRET_ACCESS_KEY],
        sqs_games_queue_name=parsed_config[_EnvKey.SQS_GAMES_QUEUE_NAME],
        github_token=parsed_config[_EnvKey.GITHUB_TOKEN])
