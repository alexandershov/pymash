import sqlalchemy as sa

from pymash import cfg
from pymash import loggers


class ScriptContext:
    def __init__(self):
        self._engine = None

    def __enter__(self) -> 'ScriptContext':
        loggers.setup_logging()
        config = cfg.get_config()
        self._engine = sa.create_engine(config.dsn)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._engine.dispose()

    @property
    def engine(self):
        assert self._engine is not None, 'use ScriptContext with the `with` statement'
        return self._engine
