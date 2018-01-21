import aiohttp_jinja2
import jinja2
import pygments
import pygments.lexers
from aiohttp import web
from pygments.formatters import html as pygments_html


def setup_jinja2(app: web.Application) -> None:
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.PackageLoader('pymash', 'templates'),
        context_processors=[aiohttp_jinja2.request_processor],
        filters={'highlight': _highlight})


def _highlight(s, language='python'):
    return _highlight_with_css_class(
        s,
        language=language,
        css_class='highlight')


def _highlight_with_css_class(text, language, css_class):
    formatter = pygments_html.HtmlFormatter(cssclass=css_class)
    return pygments.highlight(
        text,
        pygments.lexers.get_lexer_by_name(language),
        formatter)
