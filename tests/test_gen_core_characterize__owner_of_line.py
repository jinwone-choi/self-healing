import pytest
from core.characterize import _owner_of_line
import core.characterize as characterize
import ast

def test_characterize_owner_of_line_normal_input():
    code = """
def func1():
    pass

def func2():
    pass
"""
    tree = ast.parse(code)
    result = _owner_of_line(tree, 2)
    assert result == 'func1'

def test_characterize_owner_of_line_boundary_input():
    code = """
def func1():
    pass

def func2():
    pass
"""
    tree = ast.parse(code)
    result = _owner_of_line(tree, 3)  # Boundary case, end of func1
    assert result == 'func1'

def test_characterize_owner_of_line_empty_input():
    code = ""
    tree = ast.parse(code)
    result = _owner_of_line(tree, 1)
    assert result is None

def test_characterize_owner_of_line_no_function():
    code = "x = 10"
    tree = ast.parse(code)
    result = _owner_of_line(tree, 1)
    assert result is None