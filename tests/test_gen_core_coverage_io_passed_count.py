import pytest
from core.coverage_io import passed_count
import core.coverage_io as coverage_io

def test_characterize_passed_count_normal_input():
    output = "10 passed, 0 failed"
    result = passed_count(output)
    assert result == 10

def test_characterize_passed_count_empty_input():
    output = ""
    result = passed_count(output)
    assert result == 0

def test_characterize_passed_count_no_passed():
    output = "0 failed"
    result = passed_count(output)
    assert result == 0

def test_characterize_passed_count_invalid_format():
    output = "Some random text"
    result = passed_count(output)
    assert result == 0