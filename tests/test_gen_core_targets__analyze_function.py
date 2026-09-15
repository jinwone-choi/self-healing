import pytest
from core.targets import _analyze_function
import core.targets as targets
import ast

def test_characterize_analyze_function_normal_input(monkeypatch):
    code = """
def my_function():
    print("Hello, world!")
    return 42
"""
    node = ast.parse(code).body[0]
    lines = []
    imported = set()
    import_modules = {}
    result = _analyze_function(node, lines, imported, import_modules, {})
    assert result == (['print'], {'filesystem'}, False, 0)

def test_characterize_analyze_function_empty_input(monkeypatch):
    code = ""
    node = ast.parse(code)
    lines = []
    imported = set()
    import_modules = {}
    result = _analyze_function(node, lines, imported, import_modules, {})
    assert result == ([], set(), False, 0)

def test_characterize_analyze_function_with_io_calls(monkeypatch):
    code = """
from pathlib import Path

def file_operations():
    Path('myfile.txt').write_text("Hello")
"""
    node = ast.parse(code).body[0]
    lines = []
    imported = set(['Path'])
    import_modules = {}
    result = _analyze_function(node, lines, imported, import_modules, {})
    assert result == ([], set(), False, 0)
