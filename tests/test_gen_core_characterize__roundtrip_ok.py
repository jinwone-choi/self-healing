import pytest
from core.characterize import _roundtrip_ok
import core.characterize as characterize

def test_characterize_roundtrip_ok_normal_input():
    result = _roundtrip_ok("{'a': 1, 'b': 2}")
    assert result is True

def test_characterize_roundtrip_ok_empty_input():
    result = _roundtrip_ok("")
    assert result is False


def test_characterize_roundtrip_ok_with_set():
    result = _roundtrip_ok("set([1, 2, 3])")
    assert result is False
