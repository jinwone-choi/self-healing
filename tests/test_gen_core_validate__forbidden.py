import pytest
from core.validate import _forbidden
import core.validate as validate
import ast

FORBIDDEN_NAMES = ["eval", "exec"]
FORBIDDEN_IMPORT_FROM = ["os", "sys"]

def test_characterize_forbidden_import():
    code = "from os import path"
    tree = ast.parse(code)
    result = _forbidden(tree)
    assert result is None

def test_characterize_forbidden_function_call():
    code = "eval('print(1)')"
    tree = ast.parse(code)
    result = _forbidden(tree)
    assert result is None

def test_characterize_forbidden_open_write():
    code = "open('file.txt', 'w')"
    tree = ast.parse(code)
    result = _forbidden(tree)
    assert result == 'open() write with literal path'

def test_characterize_forbidden_path_write_text():
    code = "Path('file.txt').write_text('data')"
    tree = ast.parse(code)
    result = _forbidden(tree)
    assert result == 'Path(literal).write/unlink'