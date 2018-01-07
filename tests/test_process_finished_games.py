import json
from unittest import mock

import typing as tp

import boto3
import datetime as dt
import pytest

from pymash import process_finished_games
from pymash import models
from pymash.tables import *


def test_process_game_finished_event(pymash_engine, add_functions_and_repos, monkeypatch):
    game = _get_game()
    _monkeypatch_boto3(monkeypatch, [game])
    process_finished_games.main(is_infinite=False)
    _check_game_and_repos(pymash_engine, game)


def test_process_game_finished_event_twice(pymash_engine, add_functions_and_repos, monkeypatch):
    game = _get_game()
    _monkeypatch_boto3(monkeypatch, [game])
    process_finished_games.main(is_infinite=False)
    _check_game_and_repos(pymash_engine, game)
    process_finished_games.main(is_infinite=False)
    _check_game_and_repos(pymash_engine, game)


@pytest.mark.skip
def test_process_different_game_finished_event_twice(pymash_engine, add_functions_and_repos):
    game = _get_game()
    _check_game_and_repos(pymash_engine, game, game)
    changed_game = _get_game(result=models.WHITE_WINS_RESULT)
    _check_game_and_repos(pymash_engine, changed_game, game)


def _check_game_and_repos(pymash_engine, expected_game):
    _assert_game_saved(pymash_engine, expected_game)
    _assert_repo_has_rating(pymash_engine, repo_id=1, expected_rating=1791.37)
    _assert_repo_has_rating(pymash_engine, repo_id=2, expected_rating=1908.63)


@pytest.mark.skip
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


def _monkeypatch_boto3(monkeypatch, games):
    resource_mock = mock.Mock()
    resource_mock.return_value.get_queue_by_name.return_value.receive_messages.return_value = _convert_games_to_messages(
        games)
    monkeypatch.setattr(boto3, 'resource', resource_mock)


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


def _convert_games_to_messages(games: tp.List[models.Game]):
    result = []
    for a_game in games:
        body = json.dumps(_make_event_from_game(a_game))
        result.append(mock.Mock(body=body))
    return result


# TODO: remove duplication with the main code
def _make_event_from_game(game: models.Game) -> dict:
    return {
        'game_id': game.game_id,
        'white_id': game.white_id,
        'black_id': game.black_id,
        'white_score': game.result.white_score,
        'black_score': game.result.black_score,
        'occurred_at': dt.datetime.utcnow().isoformat(),
    }
