import pytest
from core.validate import parse_or_truncate
import core.validate as validate
import ast



def test_characterize_parse_or_truncate_incomplete_function():
    code = """
def test_incomplete_function(
"""
    result = parse_or_truncate(code)
    assert result == (None, '\ndef test_incomplete_function(\n', False)
