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
        return datetime < self._end

    def __repr__(self):
        return f'BannedDetails(end={self._end!a}, reason={self._reason!a})'


class Watchman:
    def __init__(self, rate_limit: float, window: dt.timedelta, ban_duration: dt.timedelta,
                 num_ips_to_trigger_gc: int = 10_000) -> None:
        assert window.total_seconds() >= 1
        assert window.total_seconds().is_integer()
        self._rate_limit = rate_limit
        self._window = window
        self._ban_duration = ban_duration
        self._info_by_ip: tp.Dict[str, _IpInfo] = collections.defaultdict(_IpInfo)
        self._num_ips_to_trigger_gc = num_ips_to_trigger_gc

    # TODO: clean it up
    def add(self, attempt: models.GameAttempt) -> None:
        info = self._info_by_ip[attempt.ip]
        info.add(attempt.at)
        at_sec = attempt.at.replace(microsecond=0)
        cur = at_sec - self._window + dt.timedelta(seconds=1)
        now = dt.datetime.utcnow()
        while cur <= at_sec and not info.is_banned_at(now):
            count = info.get_count_in_interval(cur, cur + self._window)
            cur_rate = count / self._window.total_seconds()
            if cur_rate > self._rate_limit:
                reason = f'cur_rate is {cur_rate}, rate_limit is {self._rate_limit}'
                end = now + self._ban_duration
                info.ban(end, reason)
                loggers.games_queue.info('banning ip %s till %s because %s', attempt.ip, end, reason)
            cur += dt.timedelta(seconds=1)
        if len(self._info_by_ip) >= self._num_ips_to_trigger_gc:
            self._gc(now)

    def is_banned_at(self, ip: str, datetime: dt.datetime) -> bool:
        info = self._info_by_ip[ip]
        return info.is_banned_at(datetime)

    @property
    def num_ips(self):
        return len(self._info_by_ip)

    def _gc(self, now: dt.datetime) -> None:
        for ip in list(self._info_by_ip):
            if not self.is_banned_at(ip, now):
                del self._info_by_ip[ip]


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
