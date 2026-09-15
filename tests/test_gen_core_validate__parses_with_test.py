import pytest
from core.validate import _parses_with_test
import core.validate as validate
import ast

def test_characterize_parses_with_test_normal_input():
    code = """
def test_function():
    pass
"""
    result = _parses_with_test(code)
    assert result is True

def test_characterize_parses_with_test_empty_input():
    code = ""
    result = _parses_with_test(code)
    assert result is False

def test_characterize_parses_with_test_syntax_error():
    code = "def test_function("
    result = _parses_with_test(code)
    assert result is False

def test_characterize_parses_with_test_no_test_functions():
    code = """
def regular_function():
    pass
"""
    result = _parses_with_test(code)
    assert result is False