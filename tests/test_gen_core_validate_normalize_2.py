import pytest
from core.validate import normalize
import core.validate as validate


def test_characterize_empty_input(monkeypatch):
    raw_input = ""
    target = "some_target"
    mode = "characterize"
    result = normalize(raw_input, target, mode)
    assert result.fixes == []
