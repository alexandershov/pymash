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
        if self._result is Result.WHITE_WINS:
            white_score = 1
        else:
            assert self._result is Result.BLACK_WINS
            white_score = 0
        rating_diff = self._black.rating - self._white.rating
        expected_white_score = 1 / (1 + 10 ** (rating_diff / 400))
        white_rating_change = RATING_CHANGE_COEFF * (white_score - expected_white_score)

        self._white.rating += white_rating_change
        self._black.rating -= white_rating_change
