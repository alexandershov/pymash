import textwrap

import pytest

from pymash import parser


@pytest.mark.parametrize('source_code, expected_functions', [
    # normal case
    (
            '''\
            def add(x, y):
                return x + y
            ''',
            [
                parser.Function(
                    name='add',
                    text=textwrap.dedent(
                        '''\
                        def add(x, y):
                            return x + y'''
                    )
                )
            ]
    ),
    # docstring is cut
    (
            '''\
            def add(x, y):
                """some docstring."""
                return x + y
            ''',
            [
                parser.Function(
                    name='add',
                    text=textwrap.dedent(
                        '''\
                        def add(x, y):
                            return x + y'''
                    )
                )
            ]
    ),
    # multiline docstring is cut
    (
            '''\
            def add(x, y):
                """some
                multiline
                docstring."""
                return x + y
            ''',
            [
                parser.Function(
                    name='add',
                    text=textwrap.dedent(
                        '''\
                        def add(x, y):
                            return x + y'''
                    )
                )
            ]
    ),
])
def test_get_functions(source_code, expected_functions):
    actual_functions = parser.get_functions(textwrap.dedent(source_code))
    assert actual_functions == expected_functions


@pytest.mark.parametrize('source_code, expected_exception', [
    # we refuse to parse multiline docstring with inner triple quotes: it's hard to do with regexes
    # and it's very rare case anyway
    (
            '''\
            def add(x, y):
                """some
                \\"""multiline
                docstring with inner triple quotes."""
                return x + y
            ''',
            parser.TripleQuotesDocstringError,
    ),
])
def test_get_functions_failure(source_code, expected_exception):
    with pytest.raises(expected_exception):
        parser.get_functions(textwrap.dedent(source_code))
