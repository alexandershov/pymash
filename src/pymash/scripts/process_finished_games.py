import datetime as dt
import json

import itertools

from pymash import events
from pymash import fraud
from pymash import loggers
from pymash.scripts import base


def main(iterations, wait_time_seconds=10, watchman=None):
    if watchman is None:
        watchman = _get_watchman()
    with base.ScriptContext() as context:
        for _ in iterations:
            _process_new_messages(
                watchman=watchman,
                context=context,
                wait_time_seconds=wait_time_seconds)


def _process_new_messages(watchman, context, wait_time_seconds):
    messages = context.games_queue.receive_messages(
        MaxNumberOfMessages=10, WaitTimeSeconds=wait_time_seconds)
    loggers.games_queue.info('will handle %d messages', len(messages))
    for a_message in messages:
        _process_message(
            watchman=watchman,
            context=context,
            message=a_message)
        a_message.delete()


def _process_message(watchman, context, message):
    message_dict = json.loads(message.body)
    game = events.parse_game_finished_event_as_game(message_dict)
    attempt = events.parse_game_finished_event_as_game_attempt(message_dict)
    now = dt.datetime.utcnow()
    watchman.add(now, attempt)
    if watchman.is_banned_at(attempt.ip, now):
        loggers.games_queue.info('pymash_event:is_banned skipping handling of game %s, because %s is banned',
                                 game.game_id, attempt.ip)
        return
    try:
        events.process_game_finished_event(context.engine, game)
    except events.DeletedFromDb:
        loggers.games_queue.error('pymash_event:deleted_from_db skipping handling of game %s', game.game_id,
                                  exc_info=True)


def _get_watchman():
    return fraud.Watchman(
        rate_limit=1,
        window=dt.timedelta(seconds=10),
        ban_duration=dt.timedelta(minutes=30),
        max_num_attempts_without_gc=10_000)


if __name__ == '__main__':
    main(iterations=itertools.count())
