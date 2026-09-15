import pytest
from core.integrity import _skip
import core.integrity as integrity
from pathlib import Path

def test_characterize_skip_with_excluded_directory():
    rel = Path("excluded_dir/some_file.py")
    result = _skip(rel)
    assert result is False

def test_characterize_skip_with_excluded_suffix():
    rel = Path("some_file.pyc")
    result = _skip(rel)
    assert result is True

def test_characterize_skip_with_coverage_json():
    rel = Path("some_file/coverage.json")
    result = _skip(rel)
    assert result is True

def test_characterize_skip_with_normal_file():
    rel = Path("some_file/normal_file.txt")
    result = _skip(rel)
    assert result is False