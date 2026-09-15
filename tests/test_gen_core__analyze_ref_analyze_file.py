import pytest
from core._analyze_ref import analyze_file
import core._analyze_ref as _analyze_ref
import ast


def test_characterize_analyze_file_empty_input(tmp_path):
    p = tmp_path / "empty_file.py"
    p.write_text("", encoding="utf-8")
    result = analyze_file(p, tmp_path)
    assert result == ([], ('empty_file.py', 0, 0, 0))

def test_characterize_analyze_file_syntax_error(tmp_path):
    p = tmp_path / "invalid_file.py"
    p.write_text("def func(:\n", encoding="utf-8")
    result = analyze_file(p, tmp_path)
    assert result == ([], None)
