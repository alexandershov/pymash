RATING_CHANGE_COEFF = 24


class BaseError(Exception):
    pass


class UnknownResultError(BaseError):
    pass


class GameWithYourselfError(BaseError):
    pass


class BaseResult:
    @property
    def white_score(self) -> float:
        raise NotImplementedError

    @property
    def black_score(self) -> float:
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
    def __init__(self, repo_id: str, name: str, url: str, rating: float):
        self.repo_id = repo_id
        self.name = name
        self.url = url
        self.rating = rating

    def add_rating(self, delta):
        self.rating += delta

    def sub_rating(self, delta):
        self.rating -= delta


class Function:
    def __init__(self, function_id: str, text: str) -> None:
        self.function_id = function_id
        self.text = text


class Matchup:
    def __init__(self, white_function: Function, black_function: Function) -> None:
        self.white_function = white_function
        self.black_function = black_function


# TODO(aershov182): is it okay that we store the whole repo here?
class Game:
    def __init__(self, white: Repo, black: Repo, result: BaseResult):
        if white == black:
            raise GameWithYourselfError
        self._white = white
        self._black = black
        self._result = result

    def change_ratings(self):
        white_delta = RATING_CHANGE_COEFF * (self._white_score - self._expected_white_score)

        self._white.add_rating(white_delta)
        self._black.sub_rating(white_delta)

    @property
    def _white_score(self):
        return self._result.white_score

    @property
    def _expected_white_score(self):
        rating_diff = self._black.rating - self._white.rating
        return 1 / (1 + 10 ** (rating_diff / 400))
