import datetime as dt

from pymash import fraud
from pymash import models

_IP = '127.0.0.1'
_GOOD_IP = '0.0.0.0'

_NOW = dt.datetime(2018, 1, 31, 19, 30, 27)


def test_watchman():
    watchman = _get_watchman()
    assert not watchman.is_banned_at(_IP, _NOW)
    watchman.add(_NOW, models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 25)))

    assert not watchman.is_banned_at(_IP, _NOW)
    watchman.add(_NOW, models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 26)))

    assert not watchman.is_banned_at(_IP, _NOW)
    watchman.add(_NOW, models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 27)))

    assert not watchman.is_banned_at(_IP, _NOW)
    watchman.add(_NOW, models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 27)))

    assert watchman.is_banned_at(_IP, _NOW)


def test_watchman_gc():
    watchman = _get_watchman(max_num_attempts_without_gc=5)
    watchman.add(_NOW, models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 28)))
    watchman.add(_NOW, models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 29)))
    watchman.add(_NOW, models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 30)))
    watchman.add(_NOW, models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 30)))
    watchman.add(dt.datetime(2018, 1, 31, 19, 45, 0),
                 models.GameAttempt('1.1.1.1', dt.datetime(2018, 1, 31, 19, 46, 31)))
    assert watchman.is_banned_at(_IP, _NOW)
    assert watchman.num_ips == 1


def test_kind_watchman():
    watchman = fraud.KindWatchman()
    watchman.add(_NOW, models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 28)))
    watchman.add(_NOW, models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 29)))
    watchman.add(_NOW, models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 30)))
    watchman.add(_NOW, models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 30)))
    assert not watchman.is_banned_at(_IP, _NOW)


def _get_watchman(max_num_attempts_without_gc=100):
    return fraud.Watchman(
        rate_limit=1,
        window=dt.timedelta(seconds=3),
        ban_duration=dt.timedelta(minutes=30),
        max_num_attempts_without_gc=max_num_attempts_without_gc)
