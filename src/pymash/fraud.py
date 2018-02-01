import collections
import datetime as dt
import typing as tp

from pymash import loggers
from pymash import models


class BanDetails:
    def is_banned_at(self, datetime: dt.datetime) -> bool:
        raise NotImplementedError


class NotBannedDetails(BanDetails):
    def is_banned_at(self, datetime: dt.datetime) -> bool:
        return False

    def __repr__(self):
        return f'NotBannedDetails()'


class BannedDetails(BanDetails):
    def __init__(self, end, reason):
        self._end = end
        self._reason = reason

    def is_banned_at(self, datetime: dt.datetime) -> bool:
        return self._end < datetime

    def __repr__(self):
        return f'BannedDetails(end={self._end!a}, reason={self._reason!a})'


# TODO: expire old records
class Watchman:
    def __init__(self, rate_limit: float, window: dt.timedelta, ban_duration: dt.timedelta,
                 num_attempts_before_gc: int = 1_000_000) -> None:
        assert window.total_seconds() >= 1
        assert window.total_seconds().is_integer()
        self._rate_limit = rate_limit
        self._window = window
        self._ban_duration = ban_duration
        self._attempts_by_ip: tp.Dict[str, _IpInfo] = collections.defaultdict(_IpInfo)
        self._num_attempts_before_gc = num_attempts_before_gc

    def add(self, attempt: models.GameAttempt) -> None:
        info = self._attempts_by_ip[attempt.ip]
        info.add(attempt.at)
        cur = attempt.at - self._window
        now = dt.datetime.utcnow()
        if info.is_banned_at(now):
            return
        while cur <= attempt.at + self._window:
            count = info.get_count_in_interval(cur, cur + self._window)
            cur_rate = count / self._window.total_seconds()
            if cur_rate > self._rate_limit:
                reason = f'cur_rate is {cur_rate}, rate_limit is {self._rate_limit}'
                info.ban(dt.datetime.utcnow() + self._ban_duration, reason)
            cur += dt.timedelta(seconds=1)

    def get_ban_details(self, ip: str) -> BanDetails:
        rate = self._get_cur_rate(ip)
        loggers.games_queue.info('ip %s has rate %s, rate_limit is %s', ip, rate, self._rate_limit)
        if rate > self._rate_limit:
            return BannedDetails(f'{rate} > {self._rate_limit}')
        return NotBannedDetails()

    def _get_cur_rate(self, ip) -> float:
        min_at = dt.datetime.utcnow() - self._window
        num_attempts = 0
        for attempt in self._attempts_by_ip[ip]:
            if attempt.at >= min_at:
                num_attempts += 1
        return num_attempts / self._window.total_seconds()


class _IpInfo:
    def __init__(self):
        self._count_by_second = collections.Counter()
        self._ban_details = NotBannedDetails()

    def add(self, datetime: dt.datetime) -> None:
        self._count_by_second[_convert_to_unix_ts(datetime)] += 1

    def ban(self, end, reason) -> None:
        self._ban_details = BannedDetails(end, reason)

    def is_banned_at(self, datetime):
        return self._ban_details.is_banned_at(datetime)

    def get_count_in_interval(self, start: dt.datetime, end: dt.datetime) -> int:
        result = 0
        start_ts = _convert_to_unix_ts(start)
        end_ts = _convert_to_unix_ts(end)
        for ts, count in self._count_by_second.items():
            if start_ts <= ts < end_ts:
                result += count
        return result


def _convert_to_unix_ts(datetime: dt.datetime) -> int:
    return int(datetime.replace(tzinfo=dt.timezone.utc).timestamp())
