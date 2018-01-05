import urllib.parse as urlparse

import pytest
import sqlalchemy as sa

from pymash import cfg


@pytest.fixture(scope='session')
def system_engine():
    yield from _get_engine('postgres')


@pytest.fixture(scope='session')
def pymash_engine():
    yield from _get_engine()


def _get_engine(database=None):
    config = cfg.get_config()
    if database is not None:
        dsn = _replace_database_in_dsn(config.dsn, database)
    else:
        dsn = config.dsn
    engine = sa.create_engine(dsn)
    yield engine
    engine.dispose()


def _replace_database_in_dsn(dsn, new_database):
    parsed = urlparse.urlparse(dsn)
    # noinspection PyProtectedMember
    replaced = parsed._replace(path=new_database)
    return replaced.geturl()
