import pytest
from core.characterize import fill
import core.characterize as characterize


def test_characterize_fill_empty_input(monkeypatch, tmp_path):
    test_src = ""
    captured = {"values": {}}
    header_lines = 0
    result = fill(test_src, captured, header_lines)
    assert result.ok is False
