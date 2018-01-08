import sqlalchemy as sa
from pymash import cfg
from pymash import loader


def main():
    # TODO: dry it up with create_db.py
    config = cfg.get_config()
    engine = sa.create_engine(config.dsn)
    loader.load_most_popular(
        engine, 'python', 5,
        extra_repos_full_names=['alexandershov/pymash'])
    engine.dispose()


if __name__ == '__main__':
    main()
