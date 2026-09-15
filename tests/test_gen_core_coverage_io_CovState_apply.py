import pytest
from core.coverage_io import CovState
import core.coverage_io as coverage_io


@pytest.fixture
def cov_state():
    return CovState(missing={"file1.py": {1, 2, 3}, "file2.py": {4, 5}})


def test_characterize_apply_normal_input(cov_state):
    other_executed = {"file1.py": {1, 2}, "file2.py": {4}}
    result = cov_state.apply(other_executed)
    assert result == 3


def test_characterize_apply_empty_input(cov_state):
    other_executed = {}
    result = cov_state.apply(other_executed)
    assert result == 0


def test_characterize_apply_no_matching_lines(cov_state):
    other_executed = {"file1.py": {6, 7}, "file2.py": {8, 9}}
    result = cov_state.apply(other_executed)
    assert result == 0


def test_characterize_apply_partial_matching(cov_state):
    other_executed = {"file1.py": {1, 6}, "file2.py": {4, 5}}
    result = cov_state.apply(other_executed)
    assert result == 3