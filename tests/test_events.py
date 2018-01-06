import pytest

from pymash import events
from pymash import models
from pymash.tables import *


def test_process_game_finished_event(pymash_engine, add_functions_and_repos):
    game = _get_game()
    _process_and_check(pymash_engine, game, game)


def test_process_game_finished_event_twice(pymash_engine, add_functions_and_repos):
    game = _get_game()
    _process_and_check(pymash_engine, game, game)
    _process_and_check(pymash_engine, game, game)


def test_process_different_game_finished_event_twice(pymash_engine, add_functions_and_repos):
    game = _get_game()
    _process_and_check(pymash_engine, game, game)
    changed_game = _get_game(result=models.WHITE_WINS_RESULT)
    _process_and_check(pymash_engine, changed_game, game)


def _process_and_check(pymash_engine, game, expected_game):
    events.process_game_finished_event(pymash_engine, game)
    _assert_game_saved(pymash_engine, expected_game)
    _assert_repo_has_rating(pymash_engine, repo_id=1, expected_rating=1791.37)
    _assert_repo_has_rating(pymash_engine, repo_id=2, expected_rating=1908.63)


def test_process_game_finished_event_unknown_white_id(pymash_engine, add_functions_and_repos):
    game = _get_game(white_id=1000000)
    with pytest.raises(events.NotFound):
        events.process_game_finished_event(pymash_engine, game)
    _assert_game_not_saved(pymash_engine, game)
    _assert_repo_has_rating(pymash_engine, repo_id=1, expected_rating=1800)
    _assert_repo_has_rating(pymash_engine, repo_id=2, expected_rating=1900)


def _get_game(white_id=666, black_id=777, result=models.BLACK_WINS_RESULT):
    return models.Game(
        game_id='some_game_id',
        white_id=white_id,
        black_id=black_id,
        result=result)


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
