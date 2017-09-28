import enum

RATING_COEFF = 24


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
            white_score = 0
        black_score = 1 - white_score
        rating_diff = self._black.rating - self._white.rating
        expected_white_score = 1 / (1 + 10 ** (rating_diff / 400))
        expected_black_score = 1 - expected_white_score
        self._white.rating += RATING_COEFF * (white_score - expected_white_score)
        self._black.rating += RATING_COEFF * (black_score - expected_black_score)
