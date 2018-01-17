import io
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
            '''
            def add(x, y):
                return x + y
            ''',
            _EXPECTED_RESULT
    ),
    # ignore comments after a function
    (
            '''
            def add(x, y):
                return x + y
                # some useless comment
                
            # z is equal to nine
            z = 9
            ''',
            _EXPECTED_RESULT
    ),
    # # method
    (
            '''
            class Number:
                def add(self, other):
                    return self.x + other.x
        
            import this
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
    # we refuse to parse one function
    (
            '''
            def sub(x, y):
                """multiline docstring with 
                \''' single quotes"""
                return x - y
                
            def add(x, y):
                return x + y
            ''',
            _EXPECTED_RESULT
    ),
    # async function
    (
            '''
                async def add(self, other):
                    return self.x + (await other.x)
            ''',
            [
                parser.Function(
                    name='add',
                    text=textwrap.dedent(
                        '''\
                        async def add(self, other):
                            return self.x + (await other.x)'''
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
            '''
            def add(x, y):
                """some docstring."""
                return x + y
            ''',
            _EXPECTED_RESULT
    ),
    # multiline double quotes docstring is cut
    (
            '''
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
            """
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
            """
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
            '''
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
    # we catch SyntaxError
    (
            'print "test"',
            [],
    ),
])
def test_get_functions(source_code, expected_functions):
    fileobj = io.StringIO(textwrap.dedent(source_code))
    actual_functions = parser.get_functions(fileobj, catch_exceptions=True)
    assert actual_functions == expected_functions


@pytest.mark.parametrize('source_code, expected_exception', [
    # we refuse to parse functions with only docstrings
    (
            '''
            def add(x, y):
                "Add two numbers"
            ''',
            parser.EmptyFunctionError,
    ),
    # we refuse to parse multiline docstrings with inner triple double quotes:
    # it's hard to do with regexes and it's very rare case anyway
    (
            '''
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
            '''
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
            """
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
            """
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
        parser.get_functions(io.StringIO(textwrap.dedent(source_code)))


def test_get_functions_catch_decode_error():
    # noinspection PyTypeChecker
    fileobj = io.TextIOWrapper(io.BytesIO('тест'.encode('cp1251')), encoding='utf-8')
    assert parser.get_functions(fileobj, catch_exceptions=True) == []
