import argparse

import aioboto3
import aiohttp_jinja2
import jinja2
import pygments
import pygments.lexers
from aiohttp import web
from aiopg import sa
from pygments.formatters import html as pygments_html

from pymash import cfg
from pymash import loggers
from pymash import routes
from pymash import utils


def main():
    app = create_app()
    args = _parse_args()
    web.run_app(app, host=args.host, port=args.port)


def create_app() -> web.Application:
    loggers.setup_logging()
    app = web.Application()
    config = cfg.get_config()
    app['config'] = config
    app.on_startup.append(_create_engine)
    app.on_startup.append(_create_sqs_resource)
    app.on_cleanup.append(_close_engine)
    app.on_cleanup.append(_close_sqs_resource)
    routes.setup_routes(app)
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.PackageLoader('pymash', 'templates'),
        filters={'highlight': highlight})
    return app


@utils.log_time(loggers.web)
async def _create_engine(app):
    app['db_engine'] = await sa.create_engine(app['config'].dsn, loop=app.loop)


@utils.log_time(loggers.web)
async def _close_engine(app):
    app['db_engine'].close()
    await app['db_engine'].wait_closed()


@utils.log_time(loggers.web)
async def _create_sqs_resource(app):
    config = app['config']
    app['sqs_resource'] = aioboto3.resource(
        'sqs',
        loop=app.loop,
        region_name=config.aws_region_name,
        aws_access_key_id=config.aws_access_key_id,
        aws_secret_access_key=config.aws_secret_access_key)


@utils.log_time(loggers.web)
async def _close_sqs_resource(app):
    await app['sqs_resource'].close()


def highlight_with_css_class(text, language, css_class):
    formatter = pygments_html.HtmlFormatter(cssclass=css_class)
    # TODO: can we do without strip?
    return pygments.highlight(text,
                              pygments.lexers.get_lexer_by_name(language),
                              formatter).strip()


def highlight(s, language='python'):
    return highlight_with_css_class(s, language, 'highlight')


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default='8000')
    return parser.parse_args()


if __name__ == '__main__':
    main()
