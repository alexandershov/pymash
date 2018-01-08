import sqlalchemy as sa

from pymash import cfg
from pymash import tables


def main():
    config = cfg.get_config()
    engine = sa.create_engine(config.dsn)
    tables.Base.metadata.create_all(engine)
    engine.dispose()


if __name__ == '__main__':
    main()
