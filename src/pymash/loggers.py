import logging

games_queue = logging.getLogger('pymash.games_queue')
loader = logging.getLogger('pymash.loader')
web = logging.getLogger('pymash.web')


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s')
