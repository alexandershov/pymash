import sqlalchemy as sa

from pymash import cfg
from pymash import events
from pymash import models
from pymash.tables import *


def test_process_game_finished_event(pymash_engine):
    _add_repos(pymash_engine)
    game = models.Game(
        game_id='some_game_id',
        white_id=666,
        black_id=777,
        result=models.BLACK_WINS_RESULT)
    events.process_game_finished_event(game)


# TODO: remove duplication with test_views.py
def _add_repos(pymash_engine):
    with pymash_engine.connect() as conn:
        conn.execute(Repos.insert().values(
            repo_id=1,
            name='django',
            url='https://github.com/django/django',
            rating=1800))
        conn.execute(Repos.insert().values(
            repo_id=2,
            name='flask',
            url='https://github.com/pallete/flask',
            rating=1900))
        conn.execute(Functions.insert().values(
            function_id=666,
            repo_id=1,
            text='def django(): return 1',
            random=0.3))
        conn.execute(Functions.insert().values(
            function_id=777,
            repo_id=2,
            text='def flask(): return 2',
            random=0.6))


# TODO: remove duplication with _clean_tables in test_views.py
def _clean_tables(pymash_engine):
    with pymash_engine.connect() as conn:
        for table in [Functions, Repos]:
            conn.execute(table.delete())
