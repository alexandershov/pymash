from pymash import tables
from pymash.scripts import base


def main():
    with base.ScriptContext() as context:
        tables.Base.metadata.create_all(context.engine)


if __name__ == '__main__':
    main()
