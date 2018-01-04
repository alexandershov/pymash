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
    white = _make_repo(repo_id='white_repo_id', rating=white_rating)
    black = _make_repo(repo_id='black_repo_id', rating=black_rating)
    repo_game = models.RepoGame(white, black, result)
    repo_game.change_ratings()
    _assert_ratings_equal(white.rating, expected_white_rating)
    _assert_ratings_equal(black.rating, expected_black_rating)


def test_repo_game_creation_failure():
    white = _make_repo(repo_id='repo_id', rating=1400)
    with pytest.raises(models.GameWithYourselfError):
        models.RepoGame(white, white, models.UNKNOWN_RESULT)


def _make_repo(repo_id, rating):
    return models.Repo(
        repo_id=repo_id,
        name='some_repo_name',
        url='http://some.repo.url',
        rating=rating)


def _assert_ratings_equal(actual_rating, expected_rating):
    assert actual_rating == pytest.approx(expected_rating, abs=0.01)
