import pytest
import ast
from core.validate import _forbidden
import core.validate as validate

FORBIDDEN_IMPORT_FROM = ['forbidden_module']
FORBIDDEN_NAMES = ['eval']
FORBIDDEN_CALLS = [('os', 'remove')]

def test_characterize_forbidden_import():
    code = "from forbidden_module import something"
    tree = ast.parse(code)
    result = _forbidden(tree)
    assert result is None

def test_characterize_forbidden_function_call():
    code = "eval('some code')"
    tree = ast.parse(code)
    result = _forbidden(tree)
    assert result is None

def test_characterize_forbidden_open_with_mode():
    code = "open('file.txt', mode='w')"
    tree = ast.parse(code)
    result = _forbidden(tree)
    assert result == 'open() write with literal path'

def test_characterize_forbidden_attribute_call():
    code = "os.remove('file.txt')"
    tree = ast.parse(code)
    result = _forbidden(tree)
    assert result == 'call os.remove()'