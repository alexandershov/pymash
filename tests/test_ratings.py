import pytest

from pymash import models


@pytest.mark.parametrize(
    'white_rating, black_rating, result,'
    'expected_white_rating, expected_black_rating', [
        (1400, 1400, models.Result.WHITE_WINS, 1412, 1388),
        (1400, 1400, models.Result.BLACK_WINS, 1388, 1412),
        (1800, 1400, models.Result.WHITE_WINS, 1802.18, 1397.82),
        (1800, 1400, models.Result.BLACK_WINS, 1778.18, 1421.82),
    ]
)
def test_change_ratings(
        white_rating, black_rating, result,
        expected_white_rating, expected_black_rating):
    white = models.Repo(rating=white_rating)
    black = models.Repo(rating=black_rating)
    game = models.Game(white, black, result)
    game.change_ratings()
    _assert_ratings_equal(white.rating, expected_white_rating)
    _assert_ratings_equal(black.rating, expected_black_rating)


def _assert_ratings_equal(actual_rating, expected_rating):
    assert actual_rating == pytest.approx(expected_rating, abs=0.01)
