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
    # docstring is skipped
    (
            '''\
            def add(x, y):
                """some
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
    )
])
def test_get_functions(source_code, expected_functions):
    actual_functions = parser.get_functions(textwrap.dedent(source_code))
    assert actual_functions == expected_functions
