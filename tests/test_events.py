import pytest

from pymash import events
from pymash import models
from pymash.tables import *


def test_process_game_finished_event(pymash_engine):
    _add_data(pymash_engine)
    _process_and_check(pymash_engine, _get_game())


def _test_process_game_finished_event_twice(pymash_engine):
    _add_data(pymash_engine)
    game = _get_game()
    _process_and_check(pymash_engine, game)
    _process_and_check(pymash_engine, game)


def _process_and_check(pymash_engine, game):
    events.process_game_finished_event(pymash_engine, game)
    _assert_game_saved(pymash_engine, game)
    _assert_repo_has_rating(pymash_engine, repo_id=1, expected_rating=1791.37)
    _assert_repo_has_rating(pymash_engine, repo_id=2, expected_rating=1908.63)


def test_process_game_finished_event_unknown_white_id(pymash_engine):
    _add_data(pymash_engine)
    game = _get_game(white_id=1000000)
    with pytest.raises(events.NotFound):
        events.process_game_finished_event(pymash_engine, game)
    _assert_game_not_saved(pymash_engine, game)
    _assert_repo_has_rating(pymash_engine, repo_id=1, expected_rating=1800)
    _assert_repo_has_rating(pymash_engine, repo_id=2, expected_rating=1900)


# TODO: remove duplication with test_views.py
def _add_data(pymash_engine):
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


@pytest.fixture(autouse=True)
def clean_tables(pymash_engine):
    with pymash_engine.connect() as conn:
        for table in [Games, Functions, Repos]:
            conn.execute(table.delete())


def _get_game(white_id=666, black_id=777):
    return models.Game(
        game_id='some_game_id',
        white_id=white_id,
        black_id=black_id,
        result=models.BLACK_WINS_RESULT)


def _assert_repo_has_rating(pymash_engine, repo_id, expected_rating):
    with pymash_engine.connect() as conn:
        # TODO: is there select_one?
        rows = conn.execute(Repos.select().where(Repos.c.repo_id == repo_id))

    assert list(rows)[0][Repos.c.rating] == pytest.approx(expected_rating, abs=0.01)


def _assert_game_saved(pymash_engine, game):
    with pymash_engine.connect() as conn:
        rows = list(conn.execute(Games.select().where(Games.c.game_id == game.game_id)))
    row = rows[0]
    assert row[Games.c.game_id] == game.game_id
    assert row[Games.c.white_id] == game.white_id
    assert row[Games.c.black_id] == game.black_id
    assert row[Games.c.white_score] == game.result.white_score
    assert row[Games.c.black_score] == game.result.black_score


def _assert_game_not_saved(pymash_engine, game):
    with pymash_engine.connect() as conn:
        rows = list(conn.execute(Games.select().where(Games.c.game_id == game.game_id)))
    assert len(rows) == 0
