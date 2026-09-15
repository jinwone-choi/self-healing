import pytest
from core.coverage_io import CovState
import core.coverage_io as coverage_io

def test_characterize_covstate_total_normal_input():
    st = CovState()
    st.statements = {'line1': {1, 2}, 'line2': {3, 4}}
    result = st.total
    assert result == 4

def test_characterize_covstate_total_empty_input():
    st = CovState()
    st.statements = {}
    result = st.total
    assert result == 0

def test_characterize_covstate_total_single_statement():
    st = CovState()
    st.statements = {'line1': {1}}
    result = st.total
    assert result == 1

def test_characterize_covstate_total_multiple_statements():
    st = CovState()
    st.statements = {'line1': {1}, 'line2': {2, 3}, 'line3': {4, 5, 6}}
    result = st.total
    assert result == 6