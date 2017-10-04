import pytest

from pymash import models


@pytest.mark.parametrize(
    'white_rating, black_rating, result,'
    'expected_white_rating, expected_black_rating', [
        (1400, 1400, models.WHITE_WINS_RESULT, 1412, 1388),
        (1400, 1400, models.BLACK_WINS_RESULT, 1388, 1412),
        (1800, 1400, models.WHITE_WINS_RESULT, 1802.18, 1397.82),
        (1800, 1400, models.BLACK_WINS_RESULT, 1778.18, 1421.82),
    ]
)
def test_change_ratings(
        monkeypatch,
        white_rating, black_rating, result,
        expected_white_rating, expected_black_rating):
    monkeypatch.setattr(models, 'RATING_CHANGE_COEFF', 24)
    white_repo = models.Repo(rating=white_rating)
    black_repo = models.Repo(rating=black_rating)
    white = models.Function(white_repo)
    black = models.Function(black_repo)
    game = models.Game.new(white, black, result)
    game.change_ratings()
    _assert_ratings_equal(white_repo.rating, expected_white_rating)
    _assert_ratings_equal(black_repo.rating, expected_black_rating)


def test_game_new_failure():
    repo = models.Repo(rating=1400)
    white = models.Function(repo)
    black = models.Function(repo)
    with pytest.raises(models.GameWithYourselfError):
        models.Game.new(white, black, models.UNKNOWN_RESULT)


def _assert_ratings_equal(actual_rating, expected_rating):
    assert actual_rating == pytest.approx(expected_rating, abs=0.01)
