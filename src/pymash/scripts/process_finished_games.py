import json
import time

from pymash import events
from pymash import loggers
from pymash import models
from pymash.scripts import base


def main(is_infinite=True, sleep_duration=0):
    with base.ScriptContext() as context:
        while True:
            # TODO: do we need sleeping here?
            time.sleep(sleep_duration)
            messages = context.games_queue.receive_messages(MaxNumberOfMessages=10)
            for a_message in messages:
                try:
                    events.process_game_finished_event(
                        context.engine,
                        _parse_message(json.loads(a_message.body)))
                except events.NotFound:
                    loggers.games_queue.error('skipping handling of message %r', exc_info=True)
                a_message.delete()
            if not is_infinite:
                break


def _parse_message(data: dict) -> models.Game:
    result = models.GameResult(data['white_score'], data['black_score'])
    return models.Game(
        game_id=data['game_id'],
        white_id=data['white_id'],
        black_id=data['black_id'],
        result=result)


if __name__ == '__main__':
    main(sleep_duration=10)
