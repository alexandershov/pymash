import logging

web = logging.getLogger('pymash.web')
games_queue = logging.getLogger('pymash.games_queue')
loader = logging.getLogger('pymash.loader')


def setup_logging():
    logging.basicConfig(level=logging.INFO)
