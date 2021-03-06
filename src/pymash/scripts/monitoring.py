import datetime as dt
import subprocess
import typing as tp

import boto3

from pymash.scripts import base
from pymash import loggers


class _Stats:
    def __init__(self):
        self.num_bans = 0
        self.num_skipped_games = 0
        self.num_errors = 0
        self.num_restarts = 0

    def __str__(self):
        cls_name = self.__class__.__name__
        return (
            f'{cls_name}(num_bans={self.num_bans}, num_skipped_games={self.num_skipped_games}, '
            f'num_errors={self.num_errors}, num_restarts={self.num_restarts})')

    def add_line(self, line: bytes) -> None:
        if b'pymash_event:banned_ip' in line:
            self.num_bans += 1
        if b'pymash_event:skipped_game' in line:
            self.num_skipped_games += 1
        if b'pymash_event:error' in line:
            self.num_errors += 1
        if b'scheduling restart' in line:
            self.num_restarts += 1


def main():
    loggers.setup_logging()
    now = dt.datetime.utcnow()
    end = _round_datetime(now)
    start = end - dt.timedelta(minutes=1)
    log_lines = _read_systemd_logs_in_range(start, end)
    stats = _get_stats(log_lines)
    _send_stats(stats, start)


def _send_stats(stats: _Stats, timestamp: dt.datetime) -> None:
    loggers.games_queue.info('sending stats %s', stats)
    cloudwatch = _get_cloudwatch_client()
    cloudwatch.put_metric_data(
        Namespace='pymash_background',
        MetricData=_get_metric_data(stats, timestamp))


def _get_cloudwatch_client():
    with base.ScriptContext() as context:
        config = context.config
        return boto3.client(
            'cloudwatch',
            region_name=config.aws_region_name,
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key)


def _get_metric_data(stats: _Stats, timestamp: dt.datetime):
    names_and_values = [
        ('Bans_Count', stats.num_bans),
        ('Skipped_Games_Count', stats.num_skipped_games),
        ('Errors_Count', stats.num_errors),
        ('Restarts_Count', stats.num_restarts),
    ]
    return [
        {
            'MetricName': name,
            'Value': value,
            'Unit': 'Count',
            'Timestamp': timestamp,
        }

        for name, value in names_and_values
    ]


def _round_datetime(datetime: dt.datetime) -> dt.datetime:
    return datetime.replace(second=0, microsecond=0)


def _read_systemd_logs_in_range(start: dt.datetime, end: dt.datetime) -> tp.List[bytes]:
    cmd = _make_cmd(start, end)
    output = subprocess.check_output(cmd)
    return output.splitlines()


def _get_stats(log_lines):
    stats = _Stats()
    for line in log_lines:
        stats.add_line(line)
    return stats


def _make_cmd(start, end):
    return [
        'journalctl',
        '--unit', 'pymash_background.service',
        '--since', _format_datetime(start),
        '--until', _format_datetime(end),
        '--no-pager',
        '--utc',
    ]


def _format_datetime(datetime: dt.datetime) -> str:
    return format(datetime, '%Y-%m-%d %H:%M:%S')


if __name__ == '__main__':
    main()
