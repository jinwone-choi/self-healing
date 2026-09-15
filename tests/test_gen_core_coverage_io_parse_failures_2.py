import pytest
from core.coverage_io import parse_failures
import core.coverage_io as coverage_io

def test_characterize_parse_failures_normal_input(monkeypatch):
    input_data = """
___ Section 1 ____
Line 1 of section 1
Line 2 of section 1
___ Section 2 ____
Line 1 of section 2
Line 2 of section 2
"""
    result = parse_failures(input_data)
    assert result == []

def test_characterize_parse_failures_empty_input():
    input_data = ""
    result = parse_failures(input_data)
    assert result == []

def test_characterize_parse_failures_with_exceptions(monkeypatch):
    input_data = """
___ Section with Error ____
E   Some error occurred
"""
    result = parse_failures(input_data)
    assert result == []
