import pytest
from core._analyze_ref import module_level_effects
import core._analyze_ref as _analyze_ref
import ast

def test_characterize_module_level_effects_with_function_call_assignment():
    code = """
result = some_function()
"""
    tree = ast.parse(code)
    result = module_level_effects(tree)
    assert result == 1

def test_characterize_module_level_effects_with_try_block():
    code = """
try:
    x = risky_operation()
except Exception:
    pass
"""
    tree = ast.parse(code)
    result = module_level_effects(tree)
    assert result == 1

def test_characterize_module_level_effects_empty_input():
    code = ""
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