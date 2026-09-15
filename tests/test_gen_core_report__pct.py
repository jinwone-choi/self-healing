import pytest
from core.report import _pct
import core.report as report

def test_characterize_pct_normal_input():
    result = _pct(75.5)
    assert result == '75.50%'

def test_characterize_pct_boundary_input():
    result = _pct(0)
    assert result == '0.00%'

def test_characterize_pct_none_input():
    result = _pct(None)
    assert result == 'n/a'

def test_characterize_pct_invalid_type():
    with pytest.raises(ValueError):
        _pct("invalid")