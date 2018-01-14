import boto3
import sqlalchemy as sa

from pymash import cfg
from pymash import loggers
from pymash import type_aliases as ta


class ScriptContext:
    def __init__(self):
        self._config = None
        self._engine = None
        self._sqs = None
        self._games_queue = None

    def __enter__(self) -> 'ScriptContext':
        loggers.setup_logging()
        config = cfg.get_config()
        self._config = config
        self._engine = sa.create_engine(config.dsn)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._engine.dispose()

    @property
    def engine(self) -> ta.Engine:
        _assert_is_set(self._engine)
        return self._engine

    @property
    def config(self) -> cfg.Config:
        _assert_is_set(self._config)
        return self._config

    @property
    def sqs(self):
        config = self.config
        if self._sqs is None:
            self._sqs = boto3.resource(
                'sqs',
                region_name=config.aws_region_name,
                aws_access_key_id=config.aws_access_key_id,
                aws_secret_access_key=config.aws_secret_access_key)
        return self._sqs

    @property
    def games_queue(self):
        if self._games_queue is None:
            self._games_queue = self.sqs.get_queue_by_name(
                QueueName=self.config.sqs_games_queue_name)
        return self._games_queue


def _assert_is_set(value):
    assert value is not None, 'use ScriptContext with the `with` statement'
