import pytest
from core.coverage_io import CovState
import core.coverage_io as coverage_io

def test_characterize_covstate_contribution_normal_input():
    state = CovState(missing={'file1.py': {1, 2}, 'file2.py': {3}})
    other_executed = {'file1.py': {1, 3}, 'file2.py': {4, 5}}
    result = state.contribution(other_executed)
    assert result == 1

def test_characterize_covstate_contribution_empty_input():
    state = CovState(missing={})
    other_executed = {}
    result = state.contribution(other_executed)
    assert result == 0

def test_characterize_covstate_contribution_no_matching_lines():
    state = CovState(missing={'file1.py': {1, 2}})
    other_executed = {'file1.py': {3, 4}, 'file2.py': {5}}
    result = state.contribution(other_executed)
    assert result == 0

def test_characterize_covstate_contribution_with_multiple_files():
    state = CovState(missing={'file1.py': {1, 2}, 'file2.py': {3, 4}})
    other_executed = {'file1.py': {1}, 'file2.py': {3, 5}}
    result = state.contribution(other_executed)
    assert result == 2