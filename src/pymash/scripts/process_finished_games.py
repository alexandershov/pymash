import json

from pymash import events
from pymash import loggers
from pymash.scripts import base


def main(is_infinite=True, wait_time_seconds=10):
    with base.ScriptContext() as context:
        while True:
            messages = context.games_queue.receive_messages(
                MaxNumberOfMessages=10, WaitTimeSeconds=wait_time_seconds)
            loggers.games_queue.info('will handle %d messages', len(messages))
            for a_message in messages:
                try:
                    events.process_game_finished_event(
                        context.engine,
                        events.parse_game_finished_event(json.loads(a_message.body)))
                except events.NotFound:
                    loggers.games_queue.error('skipping handling of message %r', exc_info=True)
                a_message.delete()
            if not is_infinite:
                break


if __name__ == '__main__':
    main()
