import pytest

from pymash import models


@pytest.mark.parametrize(
    'white_rating, black_rating, result,'
    'expected_white_rating, expected_black_rating', [
        (1400, 1400, models.Result.WHITE_WINS, 1412, 1412)
    ]
)
def test_change_ratings(
        white_rating, black_rating, result,
        expected_white_rating, expected_black_rating):
    white = models.Repo(rating=white_rating)
    black = models.Repo(rating=black_rating)
    game = models.Game(white, black)
    game.set_result(result)
    game.change_ratings()
    assert white.rating == pytest.approx(expected_white_rating)
    assert black.rating == pytest.approx(expected_black_rating)
