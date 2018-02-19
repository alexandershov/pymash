import datetime as dt
import subprocess
import typing as tp

import boto3

from pymash.scripts import base


class _Stats:
    def __init__(self):
        self.num_bans = 0
        self.num_skipped_games = 0
        self.num_deleted_from_db = 0
        self.num_restarts = 0

    def __str__(self):
        cls_name = self.__class__.__name__
        return (
            f'{cls_name}(num_bans={self.num_bans}, num_skipped_games={self.num_skipped_games}, '
            f'num_deleted_from_db={self.num_deleted_from_db}, num_restarts={self.num_restarts})')

    def handle_line(self, line: bytes) -> None:
        if b'pymash_event:banned_ip' in line:
            self.num_bans += 1
        if b'pymash_event:is_banned' in line:
            self.num_skipped_games += 1
        if b'pymash_event:deleted_from_db' in line:
            self.num_deleted_from_db += 1
        if b'scheduling restart' in line:
            self.num_restarts += 1


def main():
    now = dt.datetime.utcnow()
    start = _round_dtime(now - dt.timedelta(minutes=1))
    log_lines = _read_logs_in_range(start, start + dt.timedelta(minutes=1))
    stats = _get_stats(log_lines)
    _send_stats(stats, start)


def _send_stats(stats: _Stats, timestamp: dt.datetime) -> None:
    cloudwatch = _get_cloudwatch_client()
    cloudwatch.put_metric_data(
        Namespace='pymash_background',
        MetricData=_get_metric_data(stats, timestamp))


def _get_cloudwatch_client():
    with base.ScriptContext() as context:
        config = context.config
        return boto3.resource(
            'cloudwatch',
            region_name=config.aws_region_name,
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key)


def _get_metric_data(stats, timestamp):
    names_and_values = [
        ('Bans_Count', stats.num_bans),
        ('Skipped_Games_Count', stats.num_skipped_games),
        ('Deleted_From_Db_Count', stats.num_deleted_from_db),
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


def _round_dtime(dtime: dt.datetime) -> dt.datetime:
    return dtime.replace(second=0, microsecond=0)


def _read_logs_in_range(start: dt.datetime, end: dt.datetime) -> tp.List[bytes]:
    cmd = _make_cmd(start, end)
    output = subprocess.check_output(cmd)
    return output.splitlines()


def _get_stats(log_lines):
    stats = _Stats()
    for line in log_lines:
        stats.handle_line(line)
    return stats


def _make_cmd(start, end):
    return [
        'journalctl',
        '--unit', 'pymash_background.service',
        '--since', _format_dtime(start),
        '--until', _format_dtime(end),
        '--no-pager', '--utc',
    ]


def _format_dtime(dtime: dt.datetime) -> str:
    return format(dtime, '%Y-%m-%d %H:%M:%S')


if __name__ == '__main__':
    main()
