import pytest
from core._analyze_ref import module_level_effects
import core._analyze_ref as _analyze_ref
import ast

def test_characterize_module_level_effects_normal_input():
    code = """
def func():
    x = 1
    y = 2
    z = x + y
"""
    tree = ast.parse(code)
    result = module_level_effects(tree)
    assert result == 0

def test_characterize_module_level_effects_empty_input():
    code = ""
    tree = ast.parse(code)
    result = module_level_effects(tree)
    assert result == 0

def test_characterize_module_level_effects_with_assignments():
    code = """
x = 1
y = [1, 2, 3]
z = x + y
"""
    tree = ast.parse(code)
    result = module_level_effects(tree)
    assert result == 0

def test_characterize_module_level_effects_with_invalid_node():
    code = """
if True:
    pass
"""
    tree = ast.parse(code)
    result = module_level_effects(tree)
    assert result == 0