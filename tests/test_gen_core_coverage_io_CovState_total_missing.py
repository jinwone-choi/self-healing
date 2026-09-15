import pytest
from core.coverage_io import CovState
import core.coverage_io as coverage_io

def test_characterize_total_missing_normal_input():
    state = CovState(statements={'a': [1, 2], 'b': [3]}, missing={'c': [4]})
    result = state.total_missing
    assert result == 1

def test_characterize_total_missing_empty_input():
    state = CovState(statements={}, missing={})
    result = state.total_missing
    assert result == 0

def test_characterize_total_missing_boundary_input():
    state = CovState(statements={'a': []}, missing={'b': []})
    result = state.total_missing
    assert result == 0

def test_characterize_total_missing_with_large_input():
    state = CovState(statements={'a': [1]*1000, 'b': [2]*1000}, missing={'c': [3]*500})
    result = state.total_missing
    assert result == 500