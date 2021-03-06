import datetime as dt
import hashlib


class BaseError(Exception):
    pass


class MatchError(BaseError):
    pass


class MatchWithYourselfError(MatchError):
    pass


class UnknownMatchResult(MatchError):
    pass


class ResultError(BaseError):
    pass


class UnknownResultError(ResultError):
    pass


class GameError(BaseError):
    pass


class InvalidScore(GameError):
    pass


class BaseResult:
    @property
    def white_score(self) -> int:
        raise NotImplementedError

    @property
    def black_score(self) -> int:
        raise NotImplementedError

    def __eq__(self, other: 'BaseResult') -> bool:
        return (self.white_score, self.black_score) == (other.white_score, other.black_score)

    def __repr__(self):
        cls_name = self.__class__.__name__
        return f'{cls_name}({self.white_score}, {self.black_score})'


class UnknownResult(BaseResult):
    @property
    def white_score(self):
        raise UnknownResultError

    @property
    def black_score(self):
        raise UnknownResultError


class GameResult(BaseResult):
    ALLOWED_SCORES = [0, 1]

    def __init__(self, white_score, black_score):
        type(self)._check_scores(white_score, black_score)
        self._white_score = white_score
        self._black_score = black_score

    @property
    def white_score(self):
        return self._white_score

    @property
    def black_score(self):
        return self._black_score

    @classmethod
    def _check_scores(cls, white_score, black_score):
        cls._check_one_score(white_score)
        cls._check_one_score(black_score)
        if white_score + black_score != 1:
            raise InvalidScore(f'sum of scores should be 1, got {white_score} + {black_score}')

    @classmethod
    def _check_one_score(cls, score):
        if score not in cls.ALLOWED_SCORES:
            raise InvalidScore(f'{score} should be in {cls.ALLOWED_SCORES}')


WHITE_WINS_RESULT = GameResult(1, 0)
BLACK_WINS_RESULT = GameResult(0, 1)
UNKNOWN_RESULT = UnknownResult()


class GithubRepo:
    def __init__(
            self, github_id: int, name: str, full_name: str, url: str,
            zipball_url: str, num_stars: int) -> None:
        self.github_id = github_id
        self.name = name
        self.full_name = full_name
        self.url = url
        self.zipball_url = zipball_url
        self.num_stars = num_stars


class Repo:
    DEFAULT_RATING = 1800

    def __init__(self, repo_id: int, github_id: int, name: str, url: str,
                 is_active: bool, rating: float) -> None:
        self.repo_id = repo_id
        self.github_id = github_id
        self.name = name
        self.url = url
        self.is_active = is_active
        self.rating = rating

    def add_rating(self, delta: float) -> None:
        self.rating += delta

    def sub_rating(self, delta: float) -> None:
        self.rating -= delta

    def __eq__(self, other: 'Repo') -> bool:
        return self.repo_id == other.repo_id

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        return f'{cls_name}(repo_id={self.repo_id!r}, name={self.name!r}, rating={self.rating!r})'


class Function:
    def __init__(self, function_id: int, repo_id: int, is_active: bool, text: str) -> None:
        self.function_id = function_id
        self.repo_id = repo_id
        self.is_active = is_active
        self.text = text


class Match:
    RATING_CHANGE_COEFF = 24

    def __init__(self, white: Repo, black: Repo, result: BaseResult) -> None:
        if white == black:
            raise MatchWithYourselfError
        if isinstance(result, UnknownResult):
            raise UnknownMatchResult
        self.white = white
        self.black = black
        self._result = result

    def change_ratings(self) -> None:
        white_delta = self.RATING_CHANGE_COEFF * (self._white_score - self._expected_white_score)

        self.white.add_rating(white_delta)
        self.black.sub_rating(white_delta)

    @property
    def _white_score(self) -> int:
        return self._result.white_score

    @property
    def _expected_white_score(self) -> float:
        rating_diff = self.black.rating - self.white.rating
        return 1 / (1 + 10 ** (rating_diff / 400))


class GameAttempt:
    def __init__(self, ip: str, at: dt.datetime) -> None:
        self.ip = ip
        self.at = at

    def __repr__(self):
        return f'GameAttempt(ip={self.ip!a}, at={self.at})'


class Game:
    def __init__(self, game_id: str, white_id: int, black_id: int, result: BaseResult) -> None:
        self.game_id = game_id
        self.white_id = white_id
        self.black_id = black_id
        self.result = result

    def get_hash(self, salt: str) -> str:
        s = ':'.join([self.game_id, str(self.white_id), str(self.black_id), salt])
        return hashlib.sha1(s.encode('utf-8')).hexdigest()

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        return (
            f'{cls_name}(game_id={self.game_id!a}, white_id={self.white_id}, '
            f'black_id={self.black_id}, result={self.result})')
