import argparse

from pymash import loader
from pymash.scripts import base

_WHITELISTED_FULL_NAMES = (
    'alexandershov/pymash',
)
_BLACKLISTED_FULL_NAMES = (
    'isocpp/CppCoreGuidelines',
)


def main():
    args = _parse_args()
    with base.ScriptContext() as context:
        loader.load_most_popular(
            engine=context.engine,
            language=args.language,
            limit=args.limit,
            whitelisted_full_names=_WHITELISTED_FULL_NAMES,
            blacklisted_full_names=_BLACKLISTED_FULL_NAMES)


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('language')
    parser.add_argument('limit', type=int)
    return parser.parse_args()


if __name__ == '__main__':
    main()
