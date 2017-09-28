import enum

RATING_CHANGE_COEFF = 24


class Result(enum.Enum):
    WHITE_WINS = enum.auto()
    BLACK_WINS = enum.auto()
    UNKNOWN = enum.auto()


class Repo:
    def __init__(self, rating: float):
        self.rating = rating


class Game:
    def __init__(self, white: Repo, black: Repo, result: Result):
        self._white = white
        self._black = black
        self._result = result

    def change_ratings(self):
        assert self._result is not Result.UNKNOWN
        white_delta = RATING_CHANGE_COEFF * (self._white_score - self._expected_white_score)

        self._white.rating += white_delta
        self._black.rating -= white_delta

    @property
    def _white_score(self):
        if self._result is Result.WHITE_WINS:
            return 1
        else:
            assert self._result is Result.BLACK_WINS
            return 0

    @property
    def _expected_white_score(self):
        rating_diff = self._black.rating - self._white.rating
        return 1 / (1 + 10 ** (rating_diff / 400))
