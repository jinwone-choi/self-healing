import pytest
from core.coverage_io import parse_failures
import core.coverage_io as coverage_io

def test_characterize_parse_failures_normal_input(monkeypatch):
    test_input = "=== Section 1 ===\nLine 1\nLine 2\n=== Section 2 ===\nLine 3\n"
    result = parse_failures(test_input)
    assert result == []

def test_characterize_parse_failures_empty_input(monkeypatch):
    test_input = ""
    result = parse_failures(test_input)
    assert result == []

def test_characterize_parse_failures_no_sections(monkeypatch):
    test_input = "Line 1\nLine 2\nLine 3\n"
    result = parse_failures(test_input)
    assert result == []

def test_characterize_parse_failures_with_errors(monkeypatch):
    test_input = "=== Section 1 ===\nE   Some error occurred\n=== Section 2 ===\nLine 3\n"
    result = parse_failures(test_input)
    assert result == []