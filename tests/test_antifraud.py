import datetime as dt

import freezegun

from pymash import fraud
from pymash import models

_IP = '127.0.0.1'

_NOW = dt.datetime(2018, 1, 31, 19, 30, 27)


@freezegun.freeze_time(_NOW)
def test_watchman():
    watchman = _get_watchman()
    assert not watchman.is_banned_at(_IP, _NOW)
    watchman.add(models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 25)))

    assert not watchman.is_banned_at(_IP, _NOW)
    watchman.add(models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 26)))

    assert not watchman.is_banned_at(_IP, _NOW)
    watchman.add(models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 27)))

    assert not watchman.is_banned_at(_IP, _NOW)
    watchman.add(models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 27)))

    assert watchman.is_banned_at(_IP, _NOW)


# @freezegun.freeze_time(_NOW)
# def test_watchman_gc():
#     watchman = _get_watchman()
#     watchman.add(models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 28)))
#     watchman.add(models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 29)))
#     watchman.add(models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 30)))
#     freezegun.freeze_time(dt.datetime(2018, 1, 31, 19, 30, 35))
#     watchman.add(models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 31)))


def _get_watchman():
    return fraud.Watchman(
        rate_limit=1,
        window=dt.timedelta(seconds=3),
        ban_duration=dt.timedelta(minutes=30),
        num_attempts_before_gc=3)
