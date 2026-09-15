import pytest
from core.characterize import instrument
import core.characterize as characterize


def test_characterize_instrument_valid_input():
    test_src = "print('Hello')"
    out_path = "output.txt"
    result = instrument(test_src, out_path)
    assert isinstance(result, tuple)
    assert len(result) == 2
