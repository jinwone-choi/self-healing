import pytest
from core.targets import _imported_names
import core.targets as targets
import ast

def test_characterize_imported_names_normal(monkeypatch):
    tree = ast.parse("import os\nimport sys")
    names, lines, modules = _imported_names(tree)
    assert (names, lines, modules) == ({'sys', 'os'}, ['import os', 'import sys'], {'sys', 'os'})

def test_characterize_imported_names_empty(monkeypatch):
    tree = ast.parse("")
    names, lines, modules = _imported_names(tree)
    assert (names, lines, modules) == (set(), [], set())

def test_characterize_imported_names_import_from(monkeypatch):
    tree = ast.parse("from math import sqrt\nfrom os import path")
    names, lines, modules = _imported_names(tree)
    assert (names, lines, modules) == ({'path', 'sqrt'}, ['from math import sqrt', 'from os import path'], {'math', 'os'})
