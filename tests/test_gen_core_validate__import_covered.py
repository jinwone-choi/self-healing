import pytest
from core.validate import _import_covered
import core.validate as validate
import ast

def test_characterize_import_covered_normal_input(monkeypatch):
    code = """
from module import name
"""
    tree = ast.parse(code)
    line = "from module import name"
    result = _import_covered(tree, line)
    assert result is True

def test_characterize_import_covered_empty_input(monkeypatch):
    code = ""
    tree = ast.parse(code)
    line = ""
    result = _import_covered(tree, line)
    assert result is False

def test_characterize_import_covered_invalid_import(monkeypatch):
    code = """
import module
"""
    tree = ast.parse(code)
    line = "from unknown import name"
    result = _import_covered(tree, line)
    assert result is False

def test_characterize_import_covered_import_with_alias(monkeypatch):
    code = """
import module as mod
"""
    tree = ast.parse(code)
    line = "import module"
    result = _import_covered(tree, line)
    assert result is True