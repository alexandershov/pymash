import argparse

from pymash import loader
from pymash.scripts import base


def main():
    args = _parse_args()
    with base.ScriptContext() as context:
        loader.load_most_popular(
            context.engine,
            language=args.language,
            limit=args.limit,
            extra_repos_full_names=['alexandershov/pymash'])


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('language')
    parser.add_argument('limit', type=int)
    return parser.parse_args()


if __name__ == '__main__':
    main()
