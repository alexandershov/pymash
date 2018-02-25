import ast
import copy
import functools
import itertools
import math
import numbers
import re
import textwrap
import typing as tp

from pymash import loggers

_MULTILINE_DOUBLE_QUOTES_DOCSTRING_RE = re.compile(r'[ \t]*"""(?P<docstring>.*?)"""\n', re.DOTALL)
_MULTILINE_SINGLE_QUOTES_DOCSTRING_RE = re.compile(r"[ \t]*'''(?P<docstring>.*?)'''\n", re.DOTALL)

_COMMENT_LINE_RE = re.compile('^\s*#')
_BAD_CLASS_NAME_RE = re.compile('test', re.IGNORECASE)


class BaseError(Exception):
    pass


class UnknownFunctionText(BaseError):
    pass


class TripleQuotesDocstringError(UnknownFunctionText):
    pass


class EmptyFunctionError(UnknownFunctionText):
    pass


class AstSyntaxError(BaseError):
    pass


class Options:
    def __init__(self, catch_exceptions: bool, verbose: bool) -> None:
        self.catch_exceptions = catch_exceptions
        self.verbose = verbose


class _SentinelNode:
    def __init__(self, source_lines: tp.List[str]) -> None:
        self.lineno = len(source_lines) + 1
        self.col_offset = 0


@functools.total_ordering
class _Position:
    @classmethod
    def from_ast_node(cls, node):
        return cls(node.lineno, node.col_offset)

    def __init__(self, lineno: int, column: int) -> None:
        self.lineno = lineno
        self.column = column

    def __eq__(self, other: '_Position') -> bool:
        return self._as_tuple() == other._as_tuple()

    def __lt__(self, other: '_Position') -> bool:
        return self._as_tuple() < other._as_tuple()

    def _as_tuple(self):
        return self.lineno, self.column


class Function:
    def __init__(self, node, text: str, file_name: str) -> None:
        self._node = node
        self.text = text
        self.file_name = file_name
        self._cached_lines = None

    @property
    def line_number(self) -> int:
        return self._node.lineno

    @property
    def name(self):
        return self._node.name

    @property
    def num_statements(self) -> int:
        return len(self._node.body)

    @property
    def lines(self) -> tp.List[str]:
        if self._cached_lines is None:
            self._cached_lines = self.text.splitlines()
        return self._cached_lines

    def __hash__(self) -> int:
        return hash((self.name, self.text))

    def __eq__(self, other) -> bool:
        assert isinstance(other, Function)
        return (self.name, self.text) == (other.name, other.text)

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        return f'{cls_name}(name={self.name!r}, text={self.text!r})'


def get_functions(path: str, options: Options) -> tp.List[Function]:
    with open(path, encoding='utf-8') as fileobj:
        return get_functions_from_fileobj(fileobj, path, options=options)


def get_functions_from_fileobj(
        fileobj, path: str, options: Options) -> tp.List[Function]:
    try:
        source_code = fileobj.read()
    except UnicodeDecodeError:
        if not options.catch_exceptions:
            raise
        return []
    return _get_functions_from_str(source_code, path, options)


def _get_functions_from_str(
        source_code: str, file_name: str, options: Options) -> tp.List[Function]:
    source_lines = _get_lines(source_code)
    nodes = _get_ast_nodes(source_code, source_lines, options)
    functions = []
    for fn_node, next_node in _iter_function_nodes_with_next(nodes):
        try:
            text = _get_function_text(
                source_lines=source_lines,
                fn_node=fn_node,
                from_pos=_Position.from_ast_node(fn_node),
                to_pos=_Position.from_ast_node(next_node))
        except UnknownFunctionText:
            if options.verbose:
                loggers.loader.error('unknown function text', exc_info=True)
            if not options.catch_exceptions:
                raise
        else:
            fn = Function(node=fn_node, text=text, file_name=file_name)
            functions.append(fn)
    return functions


def _get_lines(source_code: str) -> tp.List[str]:
    lines = []
    cur_line_chars = []
    for char in source_code:
        cur_line_chars.append(char)
        if char == '\n':
            lines.append(''.join(cur_line_chars))
            cur_line_chars = []
    if cur_line_chars:
        lines.append(''.join(cur_line_chars))
    return lines


def _get_ast_nodes(source_code: str, source_lines: tp.List[str], options: Options):
    try:
        parsed = ast.parse(source_code)
    except SyntaxError:
        if options.verbose:
            loggers.loader.error('could not parse source', exc_info=True)
        if not options.catch_exceptions:
            raise
        return []
    nodes = copy.copy(parsed.body)
    nodes.append(_SentinelNode(source_lines))
    return nodes


def _iter_function_nodes_with_next(nodes: tp.Iterable) -> tp.Iterable[tp.Tuple]:
    result = []
    for cur_node, next_node in _iter_by_pairs(nodes):
        if isinstance(cur_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield cur_node, next_node
        elif isinstance(cur_node, ast.ClassDef):
            if _is_good_class_name(cur_node.name):
                class_nodes = itertools.chain(cur_node.body, [next_node])
                yield from _iter_function_nodes_with_next(class_nodes)
    return result


def _is_good_class_name(name):
    return _BAD_CLASS_NAME_RE.search(name) is None


def _iter_by_pairs(iterable: tp.Iterable) -> tp.Iterable:
    missing = object()
    prev = missing
    for cur in iterable:
        if prev is not missing:
            yield prev, cur
        prev = cur


def _get_function_text(source_lines, fn_node, from_pos: _Position, to_pos: _Position) -> str:
    docstring_info = _get_docstring_info(fn_node)
    fn_lines = []
    relevant_lines = source_lines[from_pos.lineno - 1:to_pos.lineno - 1]
    for lineno, line in enumerate(relevant_lines, start=from_pos.lineno):
        chars_to_add = []
        for col_offset, char in enumerate(line):
            char_pos = _Position(lineno, col_offset)
            if not docstring_info.contains(char_pos):
                chars_to_add.append(char)
        fn_lines.append(''.join(chars_to_add))
    final_fn_lines = _exclude_meaningless_lines(fn_lines)
    text = docstring_info.cut_from(''.join(final_fn_lines))
    return textwrap.dedent(text)


class _BaseDocstringInfo:
    def contains(self, pos: _Position) -> bool:
        raise NotImplementedError

    def cut_from(self, text: str) -> str:
        raise NotImplementedError


class _EmptyDocstringInfo(_BaseDocstringInfo):
    def contains(self, pos: _Position) -> bool:
        return False

    def cut_from(self, text: str) -> str:
        return text


class _DocstringInfo(_BaseDocstringInfo):
    def __init__(self, begin: _Position, end: _Position) -> None:
        self._begin = begin
        self._end = end

    def contains(self, pos: _Position) -> bool:
        # multi line docstrings are handled separately via _hacky_cut_multiline_docstring
        # because of the python bug
        if self._is_multi_line:
            return False
        return _is_position_inside(pos, self._begin, self._end)

    def cut_from(self, text: str) -> str:
        if self._is_multi_line:
            return _hacky_cut_multiline_docstring(text)
        return text

    @property
    def _is_multi_line(self):
        # ast has a bug: multiline strings have wrong start:
        # (column == -1, line number is just wrong)
        return self._begin.column == -1


def _get_docstring_info(fn_node) -> _BaseDocstringInfo:
    node = _get_docstring_node_or_none(fn_node)
    if node is None:
        return _EmptyDocstringInfo()

    if len(fn_node.body) == 1:
        raise EmptyFunctionError
    begin = _Position.from_ast_node(node)
    next_node = fn_node.body[1]
    end = _Position.from_ast_node(next_node)
    return _DocstringInfo(begin, end)


def _get_docstring_node_or_none(fn_node):
    is_first_node_expression = fn_node.body and isinstance(fn_node.body[0], ast.Expr)
    if not is_first_node_expression:
        return None
    node = fn_node.body[0]
    node_value = node.value
    if isinstance(node_value, ast.Str):
        return node
    elif isinstance(node_value, ast.Constant) and isinstance(node_value.value, str):
        return node
    else:
        return None


def _exclude_meaningless_lines(lines):
    lines = list(itertools.dropwhile(_is_empty_line, lines))
    lines = _reverse_iterable(itertools.dropwhile(_is_empty_or_comment_line, reversed(lines)))
    if lines:
        lines[-1] = lines[-1].rstrip('\r\n')
    return lines


def _reverse_iterable(iterable: tp.Iterable) -> tp.List:
    return list(reversed(list(iterable)))


def _is_empty_line(s: str) -> bool:
    if s.strip():
        return False
    return True


def is_comment_line(s: str) -> bool:
    if _COMMENT_LINE_RE.match(s) is not None:
        return True
    return False


def _is_empty_or_comment_line(s: str) -> bool:
    return _is_empty_line(s) or is_comment_line(s)


def _hacky_cut_multiline_docstring(text: str) -> str:
    regexes = [
        _MULTILINE_DOUBLE_QUOTES_DOCSTRING_RE,
        _MULTILINE_SINGLE_QUOTES_DOCSTRING_RE,
    ]
    for a_regex in sorted(regexes, key=_EarliestMatch(text)):
        if a_regex.search(text) is not None:
            return a_regex.subn(_check_and_cut_multiline_docstring, text, count=1)[0]
    return text


class _EarliestMatch:
    def __init__(self, text: str) -> None:
        self._text = text

    def __call__(self, regex) -> numbers.Number:
        match = regex.search(self._text)
        if match is None:
            return math.inf
        return match.span()[0]


def _check_and_cut_multiline_docstring(match) -> str:
    text = match.group('docstring')
    if ('"""' in text) or ("'''" in text):
        raise TripleQuotesDocstringError(text)
    if text[-1:] == '\\':
        raise TripleQuotesDocstringError(text)
    return ''


def _is_position_inside(pos: _Position, begin: _Position, end: _Position) -> bool:
    assert end.lineno >= begin.lineno
    return begin <= pos < end
