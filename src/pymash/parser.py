import ast
import re

# TODO(aershov182): better logging a whole project


# TODO(aershov182): single quotes
_MULTILINE_DOCSTRING_RE = re.compile(r'[ \t]*"""(?P<docstring>.*?)"""\n', re.DOTALL)


class BaseError(Exception):
    pass


class UnknownFunctionText(BaseError):
    pass


class TripleQuotesDocstringError(UnknownFunctionText):
    pass


class EmptyFunctionError(UnknownFunctionText):
    pass


class _End:
    def __init__(self, source_lines):
        self.lineno = len(source_lines) + 1
        self.col_offset = 0


class _Position:
    @classmethod
    def from_ast_node(cls, node):
        return cls(node.lineno, node.col_offset)

    def __init__(self, line, column):
        # TODO: rename line to lineno
        self.line = line
        self.column = column


class Function:
    def __init__(self, name, text):
        self.name = name
        self.text = text

    def __hash__(self):
        return hash((self.name, self.text))

    def __eq__(self, other):
        if not isinstance(other, Function):
            return False
        return (self.name, self.text) == (other.name, other.text)

    def __repr__(self):
        return f'{self.__class__.__name__}(name={self.name!r}, text={self.text!r})'


def get_functions(source_code: str):
    lines = source_code.splitlines(keepends=True)
    parsed = ast.parse(source_code)
    statements = list(parsed.body)
    statements.append(_End(lines))
    result = []
    for cur_st, next_st in _iter_by_pairs(statements):
        if not isinstance(cur_st, ast.FunctionDef):
            continue
        text = _get_function_text(
            source_lines=lines,
            function_node=cur_st,
            from_pos=_Position.from_ast_node(cur_st),
            to_pos=_Position.from_ast_node(next_st))
        function = Function(
            name=cur_st.name,
            text=text)
        result.append(function)
    return result


def _iter_by_pairs(iterable):
    missing = object()
    prev = missing
    for cur in iterable:
        if prev is not missing:
            yield prev, cur
        prev = cur


def _get_function_text(source_lines, function_node, from_pos: _Position, to_pos: _Position) -> str:
    docstring_node = _get_docstring_node(function_node)
    has_docstring = (docstring_node is not None)
    has_multiline_docstring = False
    if has_docstring and len(function_node.body) == 1:
        raise EmptyFunctionError
    if has_docstring:
        after_docstring_node = function_node.body[1]
        docstring_pos = _Position.from_ast_node(docstring_node)
        if _hacky_is_multiline_docstring(docstring_pos):
            has_multiline_docstring = True
        after_docstring_pos = _Position.from_ast_node(after_docstring_node)
    result = []
    # TODO: shouldn't it be `[...:to_pos.line - 1]`?
    for i, line in enumerate(source_lines[from_pos.line - 1:to_pos.line]):
        line_to_add = []
        lineno = from_pos.line + i
        for col_offset, char in enumerate(line):
            char_pos = _Position(lineno, col_offset)
            if (_is_position_inside(char_pos, from_pos, to_pos)
                    and (not has_docstring or has_multiline_docstring or not _is_position_inside(
                        char_pos, docstring_pos,
                        after_docstring_pos))):
                line_to_add.append(char)
        result.append(''.join(line_to_add))
    clean_result = []
    skipping = True
    for line in reversed(result):
        if line.strip():
            skipping = False
        if skipping:
            continue
        clean_result.append(line)
    clean_result[0] = clean_result[0].rstrip('\r\n')
    result = ''.join(reversed(clean_result))
    if has_multiline_docstring:
        return _hacky_cut_multiline_docstring(result)
    else:
        return result


def _get_docstring_node(function_node):
    has_first_expression = function_node.body and isinstance(function_node.body[0], ast.Expr)
    if not has_first_expression:
        return
    node = function_node.body[0]
    node_value = node.value
    if isinstance(node_value, ast.Str):
        return node
    elif isinstance(node_value, ast.Constant) and isinstance(node_value.value, str):
        return node
    else:
        return None


def _hacky_is_multiline_docstring(pos: _Position) -> bool:
    # ast has a bug: multiline strings have wrong start (column == -1, line number is just wrong)
    return pos.column == -1


def _hacky_cut_multiline_docstring(text: str) -> str:
    return _MULTILINE_DOCSTRING_RE.subn(_check_and_cut_multiline_docstring, text, 1)[0]


def _check_and_cut_multiline_docstring(match) -> str:
    text = match.group('docstring')
    if '"""' in text:
        raise TripleQuotesDocstringError(text)
    if text[-1:] == '\\':
        raise TripleQuotesDocstringError(text)
    return ''


def _is_position_inside(pos: _Position, begin_pos: _Position, end_pos: _Position) -> bool:
    assert end_pos.line >= begin_pos.line
    if pos.line > end_pos.line or pos.line < begin_pos.line:
        return False
    if end_pos.line == begin_pos.line:
        return begin_pos.column <= pos.column < end_pos.column
    if pos.line == begin_pos.line:
        return pos.column >= begin_pos.column
    elif pos.line == end_pos.line:
        return pos.column < end_pos.column
    else:
        return True
