import collections
import datetime as dt

from pymash import models


class Details:
    def __init__(self, is_fraud):
        self.is_fraud = is_fraud


# TODO: expire old records
class Watchman:
    def __init__(self, max_rate_limit: float, window: dt.timedelta, ban_duration: dt.timedelta) -> None:
        self._max_rate_limit = max_rate_limit
        self._window = window
        self._ban_duration = ban_duration
        self._attempts_by_ip = collections.defaultdict(list)

    def add(self, attempt: models.GameAttempt) -> None:
        self._attempts_by_ip[attempt.ip].append(attempt)

    def get_fraud_details(self, attempt: models.GameAttempt) -> Details:
        return Details(
            is_fraud=True)
