import enum
import typing as tp


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
