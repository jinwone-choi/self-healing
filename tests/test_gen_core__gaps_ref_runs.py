import pytest
from core._gaps_ref import runs
import core._gaps_ref as _gaps_ref

def test_characterize_runs_normal_input():
    result = runs([1, 2, 3, 5, 6, 7, 10])
    assert result == [(1, 3), (5, 7), (10, 10)]

def test_characterize_runs_empty_input():
    result = runs([])
    assert result == []

def test_characterize_runs_single_element():
    result = runs([5])
    assert result == [(5, 5)]

def test_characterize_runs_boundary_input():
    result = runs([1, 2, 3, 4, 6, 7, 8, 10])
    assert result == [(1, 4), (6, 8), (10, 10)]