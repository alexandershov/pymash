import ast


class _End(object):
    def __init__(self, source_lines):
        self.lineno = len(source_lines) + 1
        self.col_offset = 0


class _Position:
    @classmethod
    def from_ast_statement(cls, node):
        return cls(node.lineno, node.col_offset)

    def __init__(self, line, column):
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
        text = _get_text(
            lines,
            _Position.from_ast_statement(cur_st),
            _Position.from_ast_statement(next_st))
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


def _get_text(source_lines, from_pos: _Position, to_pos: _Position) -> str:
    result = []
    for i, line in enumerate(source_lines[from_pos.line - 1:to_pos.line]):
        is_first = (i == 0)
        is_last = (i == to_pos.line - from_pos.line)
        if is_first:
            line_to_add = line[from_pos.column:]
        elif is_last:
            # TODO: is it possible to simultaneously have is_first and is_last?
            line_to_add = line[:to_pos.column]
        else:
            line_to_add = line
        result.append(line_to_add)
    clean_result = []
    skipping = True
    for line in reversed(result):
        if line.strip():
            skipping = False
        if skipping:
            continue
        clean_result.append(line)
    clean_result[0] = clean_result[0].rstrip('\r\n')
    return ''.join(reversed(clean_result))
