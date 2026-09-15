import pytest
from core.coverage_io import CovState
import core.coverage_io as coverage_io

def test_characterize_covstate_from_json_normal():
    data = {
        "files": {
            "file1.py": {
                "executed_lines": [1, 2],
                "missing_lines": [3]
            },
            "file2.py": {
                "executed_lines": [],
                "missing_lines": [1, 2]
            }
        }
    }
    result = CovState.from_json(data)
    assert result.executed == {'file1.py': {1, 2}, 'file2.py': set()}
    assert result.missing == {'file1.py': {3}, 'file2.py': {1, 2}}
    assert result.statements == {'file1.py': {1, 2, 3}, 'file2.py': {1, 2}}

def test_characterize_covstate_from_json_empty():
    data = {
        "files": {}
    }
    result = CovState.from_json(data)
    assert result.executed == {}
    assert result.missing == {}
    assert result.statements == {}

def test_characterize_covstate_from_json_partial_data():
    data = {
        "files": {
            "file3.py": {
                "executed_lines": [4],
                "missing_lines": []
            }
        }
    }
    result = CovState.from_json(data)
    assert result.executed == {'file3.py': {4}}
    assert result.missing == {'file3.py': set()}
    assert result.statements == {'file3.py': {4}}