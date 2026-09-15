import pytest
from core.validate import static_gate
import core.validate as validate

def test_characterize_static_gate_valid_input():
    test_src = "def test_example(): assert True"
    result = static_gate(test_src)
    assert result == (False, 'no_assert', ['test_example'])

def test_characterize_static_gate_no_test_function():
    test_src = "def example(): pass"
    result = static_gate(test_src)
    assert result == (False, 'no_test_function', [])

def test_characterize_static_gate_syntax_error():
    test_src = "def test_example(:"
    result = static_gate(test_src)
    assert result == (False, 'syntax_error:invalid syntax', [])

def test_characterize_static_gate_no_assert():
    test_src = "def test_example(): pass"
    result = static_gate(test_src)
    assert result == (False, 'no_assert', ['test_example'])