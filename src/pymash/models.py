import enum

RATING_CHANGE_COEFF = 24


class BaseError(Exception):
    pass


class UnknownResultError(BaseError):
    pass


class BaseResult:
    @property
    def white_score(self):
        raise NotImplementedError

    @property
    def black_score(self):
        return 1 - self.white_score


class _UnknownResult(BaseResult):
    @property
    def white_score(self):
        raise UnknownResultError


class _Result(BaseResult):
    def __init__(self, white_score):
        self._white_score = white_score

    @property
    def white_score(self):
        return self._white_score


WHITE_WINS_RESULT = _Result(white_score=1)
BLACK_WINS_RESULT = _Result(white_score=0)
UNKNOWN_RESULT = _UnknownResult()


class Repo:
    def __init__(self, rating: float):
        self.rating = rating


class Function:
    def __init__(self, repo: Repo):
        self._repo = repo

    @property
    def repo_rating(self):
        return self._repo.rating

    @repo_rating.setter
    def repo_rating(self, new_rating):
        self._repo.rating = new_rating


class Game:
    def __init__(self, white: Function, black: Function, result: BaseResult):
        self._white = white
        self._black = black
        self._result = result

    def change_ratings(self):
        white_delta = RATING_CHANGE_COEFF * (self._white_score - self._expected_white_score)

        self._white.repo_rating += white_delta
        self._black.repo_rating -= white_delta

    @property
    def _white_score(self):
        return self._result.white_score

    @property
    def _expected_white_score(self):
        rating_diff = self._black.repo_rating - self._white.repo_rating
        return 1 / (1 + 10 ** (rating_diff / 400))
