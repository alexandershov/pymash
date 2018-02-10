import json
import typing as tp
from unittest import mock

import boto3
import pytest

from pymash import db
from pymash import events
from pymash import models
from pymash.scripts import process_finished_games
from pymash.tables import *


@pytest.mark.usefixtures('add_functions_and_repos')
def test_process_game_finished_event(pymash_engine, monkeypatch):
    game = _get_game()
    _monkeypatch_boto3(monkeypatch, [game])

    _process_and_check_finished_games(pymash_engine, game)


@pytest.mark.usefixtures('add_functions_and_repos')
def test_process_game_finished_event_twice(pymash_engine, monkeypatch):
    game = _get_game()
    _monkeypatch_boto3(monkeypatch, [game])

    _process_and_check_finished_games(pymash_engine, game)
    _process_and_check_finished_games(pymash_engine, game)


@pytest.mark.usefixtures('add_functions_and_repos')
def test_process_different_game_finished_event_twice(pymash_engine, monkeypatch):
    game = _get_game()
    _monkeypatch_boto3(monkeypatch, [game])
    _process_and_check_finished_games(pymash_engine, game)

    changed_game = _get_game(result=models.WHITE_WINS_RESULT)
    _monkeypatch_boto3(monkeypatch, [changed_game])
    _process_and_check_finished_games(pymash_engine, game)


def _process_and_check_finished_games(pymash_engine, game):
    _call_process_finished_games()
    _check_game_and_repos(pymash_engine, game)


def _call_process_finished_games(watchman=None):
    process_finished_games.main(iterations=range(1), watchman=watchman)


@pytest.mark.usefixtures('add_functions_and_repos')
def test_process_game_finished_event_unknown_white_id(pymash_engine, monkeypatch):
    game = _get_game(white_id=1000000)
    _monkeypatch_boto3(monkeypatch, [game])
    _call_process_finished_games()
    _assert_nothing_saved(pymash_engine, game)


@pytest.mark.usefixtures('add_functions_and_repos')
def test_process_game_finished_is_banned(pymash_engine, monkeypatch):
    game = _get_game()
    _monkeypatch_boto3(monkeypatch, [game])
    watchman = mock.Mock()
    watchman.is_banned_at.return_value = True
    _call_process_finished_games(watchman=watchman)
    _assert_nothing_saved(pymash_engine, game)


def _assert_nothing_saved(pymash_engine, game):
    _assert_game_not_saved(pymash_engine, game)
    _assert_repo_has_rating(pymash_engine, repo_id=1, expected_rating=1800)
    _assert_repo_has_rating(pymash_engine, repo_id=2, expected_rating=1900)


def _check_game_and_repos(pymash_engine, expected_game):
    _assert_game_saved(pymash_engine, expected_game)
    _assert_repo_has_rating(pymash_engine, repo_id=1, expected_rating=1791.37)
    _assert_repo_has_rating(pymash_engine, repo_id=2, expected_rating=1908.63)


def _get_game(white_id=666, black_id=777, result=models.BLACK_WINS_RESULT):
    return models.Game(
        game_id='some_game_id',
        white_id=white_id,
        black_id=black_id,
        result=result)


def _monkeypatch_boto3(monkeypatch, games):
    queue_mock = mock.Mock()
    queue_mock.receive_messages.return_value = _convert_games_to_messages(games)
    resource_mock = mock.Mock()
    resource_mock.return_value.get_queue_by_name.return_value = queue_mock
    monkeypatch.setattr(boto3, 'resource', resource_mock)


def _assert_repo_has_rating(pymash_engine, repo_id, expected_rating):
    with pymash_engine.connect() as conn:
        row = conn.execute(Repos.select().where(Repos.c.repo_id == repo_id)).first()
        assert row[Repos.c.rating] == pytest.approx(expected_rating, abs=0.01)


def _assert_game_saved(pymash_engine, game):
    game_from_db = db.find_game_by_id(pymash_engine, game.game_id)
    assert game_from_db.game_id == game.game_id
    assert game_from_db.white_id == game.white_id
    assert game_from_db.black_id == game.black_id
    assert game_from_db.result == game.result


def _assert_game_not_saved(pymash_engine, game):
    with pymash_engine.connect() as conn:
        num_games_query = Games.count().where(Games.c.game_id == game.game_id)
        num_rows = conn.execute(num_games_query).scalar()
        assert num_rows == 0


def _convert_games_to_messages(games: tp.List[models.Game]):
    result = []
    for a_game in games:
        body = json.dumps(events.make_game_finished_event('127.0.0.1', a_game))
        result.append(mock.Mock(body=body))
    return result
