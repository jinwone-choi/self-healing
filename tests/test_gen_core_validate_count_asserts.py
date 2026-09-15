import pytest
from core.validate import count_asserts
import core.validate as validate

def test_characterize_count_asserts_normal_input():
    code = """
def test_example():
    assert True
    assert 1 == 1
"""
    result = count_asserts(code)
    assert result == (1, 2)

def test_characterize_count_asserts_empty_input():
    code = ""
    result = count_asserts(code)
    assert result == (0, 0)

def test_characterize_count_asserts_syntax_error():
    code = "def test_example(:"
    result = count_asserts(code)
    assert result == (0, 0)

def test_characterize_count_asserts_no_asserts():
    code = """
def test_example():
    pass
"""
    result = count_asserts(code)
    assert result == (1, 0)