import pytest
from core.validate import strip_functions
import core.validate as validate

def test_characterize_strip_functions_normal_input():
    src = """
def keep_me():
    return True

def remove_me():
    return False
"""
    names = {"remove_me"}
    result = strip_functions(src, names)
    assert result == '\ndef keep_me():\n    return True\n'

def test_characterize_strip_functions_empty_input():
    src = ""
    names = {"remove_me"}
    result = strip_functions(src, names)
    assert result == '\n'

def test_characterize_strip_functions_no_names():
    src = """
def func_one():
    return 1

def func_two():
    return 2
"""
    names = set()
    result = strip_functions(src, names)
    assert result == '\ndef func_one():\n    return 1\n\ndef func_two():\n    return 2\n'

def test_characterize_strip_functions_with_decorators():
    src = """
@decorator
def remove_me():
    return False

def keep_me():
    return True
"""
    names = {"remove_me"}
    result = strip_functions(src, names)
    assert result == '\n\ndef keep_me():\n    return True\n'