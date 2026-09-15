import pytest
from core.prompt import estimate_tokens
import core.prompt as prompt

def test_characterize_estimate_tokens_normal_input():
    result = estimate_tokens("Hello, world!")
    assert result == 3

def test_characterize_estimate_tokens_empty_input():
    result = estimate_tokens("")
    assert result == 0

def test_characterize_estimate_tokens_boundary_input():
    result = estimate_tokens("abcd" * 4)  # 16 ASCII characters
    assert result == 4

def test_characterize_estimate_tokens_non_ascii_input():
    result = estimate_tokens("안녕하세요")  # Korean characters
    assert result == 5