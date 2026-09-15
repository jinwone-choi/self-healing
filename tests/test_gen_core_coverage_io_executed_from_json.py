import pytest
from core.coverage_io import executed_from_json
import core.coverage_io as coverage_io

def test_characterize_executed_from_json_normal_input():
    data = {
        "files": {
            "file1.py": {"executed_lines": [1, 2, 3]},
            "file2.py": {"executed_lines": [4, 5]}
        }
    }
    result = executed_from_json(data)
    assert result == {'file1.py': {1, 2, 3}, 'file2.py': {4, 5}}

def test_characterize_executed_from_json_empty_input():
    data = {
        "files": {}
    }
    result = executed_from_json(data)
    assert result == {}

def test_characterize_executed_from_json_missing_executed_lines():
    data = {
        "files": {
            "file1.py": {}
        }
    }
    result = executed_from_json(data)
    assert result == {'file1.py': set()}

def test_characterize_executed_from_json_invalid_data_type():
    with pytest.raises(AttributeError):
        executed_from_json("invalid_data")