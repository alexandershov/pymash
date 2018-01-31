import datetime as dt

import freezegun

from pymash import fraud
from pymash import models

_IP = '127.0.0.1'

_NOW = dt.datetime(2018, 1, 31, 19, 30, 27)


def test_not_a_frauder():
    watchman = _get_watchman()
    with freezegun.freeze_time(_NOW):
        details = watchman.get_fraud_details(_IP)
    assert not details.is_fraud


@freezegun.freeze_time(_NOW)
def test_frauder():
    watchman = _get_watchman()
    watchman.add(models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 25)))
    watchman.add(models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 26)))
    assert not watchman.get_fraud_details(_IP).is_fraud
    watchman.add(models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 27)))
    assert not watchman.get_fraud_details(_IP).is_fraud
    watchman.add(models.GameAttempt(_IP, dt.datetime(2018, 1, 31, 19, 30, 27)))
    assert watchman.get_fraud_details(_IP).is_fraud


def _get_watchman():
    return fraud.Watchman(
        rate_limit=1,
        window=dt.timedelta(seconds=3),
        ban_duration=dt.timedelta(minutes=30))
