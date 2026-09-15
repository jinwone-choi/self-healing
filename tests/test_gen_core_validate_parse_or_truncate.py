import pytest
from core.validate import parse_or_truncate
import core.validate as validate
import ast



def test_characterize_parse_or_truncate_syntax_error():
    code = "def func():\n    print('Hello'\n"
    result = parse_or_truncate(code)
    assert result == (None, "def func():\n    print('Hello'\n", False)
