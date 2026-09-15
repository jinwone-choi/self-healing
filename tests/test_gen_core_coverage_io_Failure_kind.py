import pytest
from core.coverage_io import Failure
import core.coverage_io as coverage_io

def test_characterize_failure_kind_did_not_raise():
    failure = Failure(nodeid="test_example", test_name="test_example", exc_type="Exception", message="DID NOT RAISE")
    result = failure.kind
    assert result == "did_not_raise"

def test_characterize_failure_kind_timeout():
    failure = Failure(nodeid="test_example", test_name="test_example", exc_type="TimeoutError", message="Timeout occurred")
    result = failure.kind
    assert result == "timeout"

def test_characterize_failure_kind_collection_error():
    failure = Failure(nodeid="test_example", test_name=None, exc_type="Exception", message="Some error occurred")
    result = failure.kind
    assert result == "collection_error"

def test_characterize_failure_kind_fixture_not_found():
    failure = Failure(nodeid="test_example", test_name="test_example", exc_type="Exception", message="fixture not found")
    result = failure.kind
    assert result == "fixture_not_found"