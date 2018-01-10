import argparse

import sqlalchemy as sa

from pymash import cfg
from pymash import loader
from pymash import loggers


def main():
    loggers.setup_logging()
    # TODO: dry it up with create_db.py
    args = _parse_args()
    config = cfg.get_config()
    engine = sa.create_engine(config.dsn)
    loader.load_most_popular(
        engine,
        language=args.language,
        limit=args.limit,
        extra_repos_full_names=['alexandershov/pymash'])
    engine.dispose()


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('language')
    parser.add_argument('limit', type=int)
    return parser.parse_args()


if __name__ == '__main__':
    main()
