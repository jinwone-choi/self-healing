import pytest
from core.coverage_io import PytestResult
import core.coverage_io as coverage_io

def test_characterize_pytest_result_ok_success():
    result = PytestResult(returncode=0, stdout="", stderr="")
    assert result.ok is True

def test_characterize_pytest_result_ok_failure():
    result = PytestResult(returncode=5, stdout="", stderr="")
    assert result.ok is True

def test_characterize_pytest_result_ok_non_zero():
    result = PytestResult(returncode=1, stdout="", stderr="")
    assert result.ok is False

def test_characterize_pytest_result_ok_negative():
    result = PytestResult(returncode=-1, stdout="", stderr="")
    assert result.ok is False