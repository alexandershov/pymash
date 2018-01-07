import json

import boto3
import sqlalchemy as sa

from pymash import cfg
from pymash import events
from pymash import models


def main(is_infinite=True):
    config = cfg.get_config()
    sqs = boto3.resource(
        'sqs',
        region_name=config.aws_region,
        aws_access_key_id=config.aws_access_key_id,
        aws_secret_access_key=config.aws_secret_access_key)
    games_queue = sqs.get_queue_by_name(QueueName=config.sqs_games_queue_name)
    engine = sa.create_engine(config.dsn)
    while True:
        messages = games_queue.receive_messages(MaxNumberOfMessages=10)
        for a_message in messages:
            try:
                events.process_game_finished_event(
                    engine,
                    _parse_message(json.loads(a_message.body)))
            except events.NotFound as exc:
                print(f'skipping {a_message!r} because of {exc}')
            a_message.delete()
        if not is_infinite:
            break
    engine.dispose()


def _parse_message(data: dict) -> models.Game:
    result = models.GameResult(data['white_score'], data['black_score'])
    return models.Game(
        game_id=data['game_id'],
        white_id=data['white_id'],
        black_id=data['black_id'],
        result=result)


if __name__ == '__main__':
    main()