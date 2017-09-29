import argparse

from aiohttp import web

from pymash import routes


def main():
    args = _parse_args()
    app = web.Application()
    routes.setup_routes(app)
    web.run_app(app, host=args.host, port=args.port)


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', required=True)
    parser.add_argument('--port', type=int, required=True)
    return parser.parse_args()


if __name__ == '__main__':
    main()
