import argparse

from aiohttp import web

from pymash import routes


def main():
    app = create_app()
    args = _parse_args()
    web.run_app(app, host=args.host, port=args.port)


def create_app() -> web.Application:
    app = web.Application()
    routes.setup_routes(app)
    return app


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default='8000')
    return parser.parse_args()


if __name__ == '__main__':
    main()
