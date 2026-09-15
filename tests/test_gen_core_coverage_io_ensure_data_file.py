import pytest
from core.coverage_io import ensure_data_file
import core.coverage_io as coverage_io
from pathlib import Path

def test_characterize_ensure_data_file_creates_file(tmp_path):
    data_file = tmp_path / "coverage_data_file"
    ensure_data_file(data_file)
    assert data_file.exists() is True

def test_characterize_ensure_data_file_no_creation_if_exists(tmp_path):
    data_file = tmp_path / "coverage_data_file"
    data_file.touch()  # Create the file
    ensure_data_file(data_file)
    assert data_file.exists() is True


def test_characterize_ensure_data_file_invalid_type(tmp_path):
    with pytest.raises(AttributeError):
        ensure_data_file(None)
