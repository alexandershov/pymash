import json
import time

from pymash import events
from pymash import loggers
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
                        events.parse_game_finished_event(json.loads(a_message.body)))
                except events.NotFound:
                    loggers.games_queue.error('skipping handling of message %r', exc_info=True)
                a_message.delete()
            if not is_infinite:
                break


if __name__ == '__main__':
    main(sleep_duration=10)
