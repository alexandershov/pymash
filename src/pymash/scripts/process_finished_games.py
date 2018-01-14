import json

import itertools

from pymash import events
from pymash import loggers
from pymash.scripts import base


def main(iterations, wait_time_seconds=10):
    with base.ScriptContext() as context:
        for _ in iterations:
            _process_new_messages(context, wait_time_seconds)


def _process_new_messages(context, wait_time_seconds):
    messages = context.games_queue.receive_messages(
        MaxNumberOfMessages=10, WaitTimeSeconds=wait_time_seconds)
    loggers.games_queue.info('will handle %d messages', len(messages))
    for a_message in messages:
        _process_message(context, a_message)
        a_message.delete()


def _process_message(context, message):
    message_dict = json.loads(message.body)
    game = events.parse_game_finished_event(message_dict)
    try:
        events.process_game_finished_event(context.engine, game)
    except events.DeletedFromDb:
        loggers.games_queue.error('skipping handling of game %s', game.game_id, exc_info=True)


if __name__ == '__main__':
    main(iterations=itertools.count())
