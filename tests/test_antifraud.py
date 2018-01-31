import datetime as dt

from pymash import fraud
from pymash import models


def test_antifraud():
    watchman = fraud.Watchman(
        max_rate_limit=1,
        window=dt.timedelta(seconds=3),
        ban_duration=dt.timedelta(minutes=30))
    watchman.add(models.GameAttempt('127.0.0.1', dt.datetime(2018, 1, 31, 19, 25)))
    watchman.add(models.GameAttempt('127.0.0.1', dt.datetime(2018, 1, 31, 19, 26)))
    watchman.add(models.GameAttempt('127.0.0.1', dt.datetime(2018, 1, 31, 19, 27)))
    details = watchman.get_fraud_details(models.GameAttempt('127.0.0.1', dt.datetime(2018, 1, 31, 19, 27)))
    assert details.is_fraud
