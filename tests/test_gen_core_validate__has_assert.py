import pytest
from core.validate import _has_assert
import core.validate as validate
import ast

def test_characterize_has_assert_with_assert_statement():
    code = """
def test_example():
    assert a == b
"""
    tree = ast.parse(code)
    result = _has_assert(tree.body[0])
    assert result is True

def test_characterize_has_assert_with_with_context():
    code = """
def test_example():
    with pytest.raises(ValueError):
        raise ValueError("Error")
"""
    tree = ast.parse(code)
    result = _has_assert(tree.body[0])
    assert result is True

def test_characterize_has_assert_with_empty_function():
    code = """
def test_empty():
    pass
"""
    tree = ast.parse(code)
    result = _has_assert(tree.body[0])
    assert result is False

def test_characterize_has_assert_with_cap_exc_context():
    code = """
def test_example():
    with __cap_exc():
        raise Exception("Error")
"""
    tree = ast.parse(code)
    result = _has_assert(tree.body[0])
    assert result is False