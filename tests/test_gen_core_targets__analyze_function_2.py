import pytest
from core.targets import _analyze_function
import core.targets as targets
import ast

def test_characterize_analyze_function_normal_input():
    code = """
def example_func():
    print("Hello, World!")
"""
    tree = ast.parse(code)
    result = _analyze_function(tree.body[0], [], set(), set(), {})
    assert result == (['print'], {'filesystem'}, False, 0)

def test_characterize_analyze_function_with_imported():
    code = """
import os

def example_func():
    os.remove("file.txt")
"""
    tree = ast.parse(code)
    imported = {'os'}
    from_imports = {'os': 'os'}
    result = _analyze_function(tree.body[1], [], imported, set(), from_imports)
    assert result == (['os.remove'], {'filesystem'}, False, 0)

def test_characterize_analyze_function_with_attribute_access():
    code = """
class Example:
    def method(self):
        self.attr.write_text("data")

example = Example()
example.method()
"""
    tree = ast.parse(code)
    imported = set()
    from_imports = {}
    result = _analyze_function(tree.body[1], [], imported, set(), from_imports)
    assert result == ([], set(), False, 0)
