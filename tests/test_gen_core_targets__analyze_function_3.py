import pytest
from core.targets import _analyze_function
import core.targets as targets
import ast

def test_characterize_analyze_function_normal_input():
    code = """
def example_func():
    print("Hello, World!")
    return 42
"""
    tree = ast.parse(code)
    result = _analyze_function(tree.body[0], [], set(), set(), {})
    assert result == (['print'], {'filesystem'}, False, 0)

def test_characterize_analyze_function_imported_function():
    code = """
from math import sqrt
def example_func():
    return sqrt(16)
"""
    tree = ast.parse(code)
    mock_imports = {'sqrt': 'math'}
    targets.IO_NAMES = {"print"}
    targets.IO_MODULES = {"math": "math"}
    
    result = _analyze_function(tree.body[1], [], set(mock_imports.keys()), set(), mock_imports)
    assert result == (['math.sqrt'], {'math'}, True, 0)

def test_characterize_analyze_function_with_attributes():
    code = """
class Example:
    def method(self):
        pass
"""
    tree = ast.parse(code)
    result = _analyze_function(tree.body[0], [], set(), set(), {})
    assert result == ([], set(), False, 0)
