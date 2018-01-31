import collections
import datetime as dt
import typing as tp

from pymash import loggers
from pymash import models


class BaseDetails:
    @property
    def is_fraud(self):
        raise NotImplementedError


class GoodDetails(BaseDetails):
    @property
    def is_fraud(self):
        return False

    def __repr__(self):
        return f'GoodDetails()'


class BadDetails(BaseDetails):
    def __init__(self, reason):
        self._reason = reason

    @property
    def is_fraud(self):
        return True

    def __repr__(self):
        return f'BadDetails(reason={self._reason!a})'


# TODO: expire old records
class Watchman:
    def __init__(self, rate_limit: float, window: dt.timedelta, ban_duration: dt.timedelta) -> None:
        assert window.total_seconds() >= 1
        self._rate_limit = rate_limit
        self._window = window
        self._ban_duration = ban_duration
        self._attempts_by_ip: tp.Dict[str, tp.List[models.GameAttempt]] = collections.defaultdict(list)

    def add(self, attempt: models.GameAttempt) -> None:
        self._attempts_by_ip[attempt.ip].append(attempt)

    def get_fraud_details(self, ip: str) -> BaseDetails:
        rate = self._get_cur_rate(ip)
        loggers.games_queue.info('ip %s has rate %s, rate_limit is %s', ip, rate, self._rate_limit)
        if rate > self._rate_limit:
            return BadDetails(f'{rate} > {self._rate_limit}')
        return GoodDetails()

    def _get_cur_rate(self, ip) -> float:
        min_at = dt.datetime.utcnow() - self._window
        num_attempts = 0
        for attempt in self._attempts_by_ip[ip]:
            if attempt.at >= min_at:
                num_attempts += 1
        return num_attempts / self._window.total_seconds()
