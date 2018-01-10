import logging

web = logging.getLogger('pymash.web')
games_queue = logging.getLogger('pymash.games_queue')


def setup_logging():
    logging.basicConfig(level=logging.INFO)
