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
    def __init__(self, white: Repo, black: Repo):
        self.white = white
        self.black = black
        self.result = Result.UNKNOWN

    def set_result(self, result: Result):
        self.result = result

    def change_ratings(self):
        assert self.result is not Result.UNKNOWN
