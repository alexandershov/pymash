import collections
import datetime as dt
import typing as tp

from pymash import loggers
from pymash import models


class _BanDetails:
    def is_banned_at(self, datetime: dt.datetime) -> bool:
        raise NotImplementedError


class _NotBannedDetails(_BanDetails):
    def is_banned_at(self, datetime: dt.datetime) -> bool:
        return False

    def __repr__(self):
        return '_NotBannedDetails()'


class _BannedDetails(_BanDetails):
    def __init__(self, end, reason):
        self._end = end
        self._reason = reason

    def is_banned_at(self, datetime: dt.datetime) -> bool:
        return datetime < self._end

    def __repr__(self):
        return f'_BannedDetails(end={self._end!a}, reason={self._reason!a})'


class _User:
    def __init__(self):
        self._num_attempts_by_unix_ts = collections.Counter()
        self._ban_details = _NotBannedDetails()

    def record_attempt_at(self, datetime: dt.datetime) -> None:
        self._num_attempts_by_unix_ts[_convert_to_unix_ts(datetime)] += 1

    def ban(self, end, reason) -> None:
        self._ban_details = _BannedDetails(end, reason)

    def is_banned_at(self, datetime: dt.datetime) -> bool:
        return self._ban_details.is_banned_at(datetime)

    def get_num_attempts_in_interval(self, start: dt.datetime, end: dt.datetime) -> int:
        num_attempts = 0
        start_ts = _convert_to_unix_ts(start)
        end_ts = _convert_to_unix_ts(end)
        for ts, count in self._num_attempts_by_unix_ts.items():
            if start_ts <= ts < end_ts:
                num_attempts += count
        return num_attempts


class BaseWatchman:
    def add(self, now: dt.datetime, attempt: models.GameAttempt) -> None:
        raise NotImplementedError

    def is_banned_at(self, ip: str, datetime: dt.datetime) -> bool:
        raise NotImplementedError


class KindWatchman(BaseWatchman):
    def add(self, now: dt.datetime, attempt: models.GameAttempt) -> None:
        pass

    def is_banned_at(self, ip: str, datetime: dt.datetime) -> bool:
        return False


class Watchman(BaseWatchman):
    def __init__(self, rate_limit: float, window: dt.timedelta, ban_duration: dt.timedelta,
                 max_num_attempts_without_gc: int) -> None:
        assert window.total_seconds() >= 1
        assert window.total_seconds().is_integer()
        self._rate_limit = rate_limit
        self._window = window
        self._ban_duration = ban_duration
        self._user_by_ip: tp.Dict[str, _User] = collections.defaultdict(_User)
        self._num_attempts_without_gc = 0
        self._max_num_attempts_without_gc = max_num_attempts_without_gc

    def add(self, now: dt.datetime, attempt: models.GameAttempt) -> None:
        self._num_attempts_without_gc += 1
        user = self._user_by_ip[attempt.ip]
        user.record_attempt_at(attempt.at)
        for datetime in self._rate_affecting_datetimes(attempt):
            rate = self._get_rate(user, start=datetime)
            if rate > self._rate_limit:
                self._ban(attempt=attempt, user=user, rate=rate, now=now)

        self._gc(now)

    def is_banned_at(self, ip: str, datetime: dt.datetime) -> bool:
        user = self._user_by_ip[ip]
        return user.is_banned_at(datetime)

    @property
    def num_ips(self) -> int:
        return len(self._user_by_ip)

    def _rate_affecting_datetimes(self, attempt: models.GameAttempt) -> tp.Iterable[dt.datetime]:
        at_exact_sec = attempt.at.replace(microsecond=0)
        start = at_exact_sec - self._window + dt.timedelta(seconds=1)
        yield from _datetimes_between(start, at_exact_sec, step=dt.timedelta(seconds=1))

    def _get_rate(self, user: _User, start: dt.datetime) -> float:
        count = user.get_num_attempts_in_interval(start, start + self._window)
        return count / self._window.total_seconds()

    def _ban(self, attempt: models.GameAttempt, user: _User, rate: float, now: dt.datetime) -> None:
        reason = f'cur_rate is {rate}, rate_limit is {self._rate_limit}'
        end = now + self._ban_duration
        user.ban(end, reason)
        loggers.games_queue.info('pymash_event:banned_ip %s till %s because %s', attempt.ip, end, reason)

    def _needs_gc(self) -> bool:
        return self._num_attempts_without_gc >= self._max_num_attempts_without_gc

    def _gc(self, now: dt.datetime) -> None:
        if not self._needs_gc():
            return
        for ip in list(self._user_by_ip):
            if not self.is_banned_at(ip, now):
                del self._user_by_ip[ip]
        self._num_attempts_without_gc = 0


def _convert_to_unix_ts(datetime: dt.datetime) -> int:
    return int(datetime.replace(tzinfo=dt.timezone.utc).timestamp())


def _datetimes_between(first: dt.datetime, last: dt.datetime, step: dt.timedelta) -> tp.Iterable[dt.datetime]:
    cur = first
    while cur <= last:
        yield cur
        cur += step
