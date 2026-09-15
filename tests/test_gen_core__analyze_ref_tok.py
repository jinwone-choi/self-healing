import pytest
from core._analyze_ref import tok
import core._analyze_ref as _analyze_ref

def test_characterize_tok_normal_input():
    result = tok("This is a test string.")
    assert result == 5

def test_characterize_tok_empty_input():
    result = tok("")
    assert result == 0

def test_characterize_tok_boundary_input():
    result = tok("abcd")
    assert result == 1

def test_characterize_tok_invalid_type():
    with pytest.raises(TypeError):
        tok(123)