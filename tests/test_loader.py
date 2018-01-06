from pymash import loader
from pymash.tables import *


def test_load_most_popular(pymash_engine):
    loader.load_most_popular()
    _assert_repo_was_loaded(pymash_engine)


def _assert_repo_was_loaded(pymash_engine):
    with pymash_engine.connect() as conn:
        rows = list(conn.execute(Repos.select()))
    assert len(rows) == 1
