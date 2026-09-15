import pytest
from core.loop import _safe
import core.loop as loop

def test_characterize_safe_normal_input():
    result = _safe("Hello World!")
    assert result == 'Hello_World_'

def test_characterize_safe_boundary_input():
    result = _safe("")
    assert result == ''

def test_characterize_safe_special_characters():
    result = _safe("Test@123#")
    assert result == 'Test_123_'

def test_characterize_safe_numeric_string():
    result = _safe("12345")
    assert result == '12345'