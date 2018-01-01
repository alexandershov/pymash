import textwrap

import pytest

from pymash import parser

_EXPECTED_RESULT = [
    parser.Function(
        name='add',
        text=textwrap.dedent(
            '''\
            def add(x, y):
                return x + y'''
        )
    ),
]


@pytest.mark.parametrize('source_code, expected_functions', [
    # normal case
    (
            '''\
            def add(x, y):
                return x + y
            ''',
            _EXPECTED_RESULT
    ),
    # method
    (
            '''\
            class Number:
                def add(self, other):
                    return self.x + other.x
            ''',
            [
                parser.Function(
                    name='add',
                    text=textwrap.dedent(
                        '''\
                        def add(self, other):
                            return self.x + other.x'''
                    )
                ),
            ]
    ),
    # single statement function
    (
            '''def add(x, y): return x + y''',
            [
                parser.Function(
                    name='add',
                    text='''def add(x, y): return x + y'''
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
            _EXPECTED_RESULT
    ),
    # multiline double quotes docstring is cut
    (
            '''\
            def add(x, y):
                """some
                multiline
                docstring."""
                return x + y
            ''',
            _EXPECTED_RESULT
    ),
    # multiline single quotes docstring is cut
    (
            """\
            def add(x, y):
                '''some
                multiline
                docstring.'''
                return x + y
            """,
            _EXPECTED_RESULT
    ),
    # we don't touch literals in body (single quotes docstring)
    (
            """\
            def add(x, y):
                '''some
                multiline
                docstring.'''
                s = \"""
                    some string\"""
                return x + y
            """,
            [
                parser.Function(
                    name='add',
                    text=textwrap.dedent(
                        '''\
                        def add(x, y):
                            s = \"""
                                some string\"""
                            return x + y'''
                    )
                )
            ]
    ),
    # we don't touch literals in body (double quotes docstring)
    (
            '''\
            def add(x, y):
                """some
                multiline
                docstring."""
                s = \'''
                    some string\'''
                return x + y
            ''',
            [
                parser.Function(
                    name='add',
                    text=textwrap.dedent(
                        '''\
                        def add(x, y):
                            s = \'''
                                some string\'''
                            return x + y'''
                    )
                )
            ]
    ),
    # nothing to parse
    (
            '',
            [],
    ),

])
def test_get_functions(source_code, expected_functions):
    actual_functions = parser.get_functions(textwrap.dedent(source_code))
    assert actual_functions == expected_functions


@pytest.mark.parametrize('source_code, expected_exception', [
    # we refuse to parse functions with only docstrings
    (
            '''\
            def add(x, y):
                "Add two numbers"
            ''',
            parser.EmptyFunctionError,
    ),
    # we refuse to parse multiline docstrings with inner triple double quotes:
    # it's hard to do with regexes and it's very rare case anyway
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
    # we refuse to parse multiline docstrings with quoted inner double quotes: rare case
    (
            '''\
            def add(x, y):
                """some
                \\"""
                multiline
                docstring with inner triple quotes ending on newline."""
                return x + y
            ''',
            parser.TripleQuotesDocstringError,
    ),
    # we refuse to parse multiline docstrings with inner triple single quotes:
    # it's hard to do with regexes and it's very rare case anyway
    (
            """\
            def add(x, y):
                '''some
                \\'''multiline
                docstring with inner triple quotes.'''
                return x + y
            """,
            parser.TripleQuotesDocstringError,
    ),
    # we refuse to parse multiline docstrings with quoted inner single quotes: rare case
    (
            """\
            def add(x, y):
                '''some
                \\'''
                multiline
                docstring with inner triple quotes ending on newline.'''
                return x + y
            """,
            parser.TripleQuotesDocstringError,
    ),
])
def test_get_functions_failure(source_code, expected_exception):
    with pytest.raises(expected_exception):
        parser.get_functions(textwrap.dedent(source_code))
