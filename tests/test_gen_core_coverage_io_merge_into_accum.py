import pytest
from core.coverage_io import merge_into_accum
import core.coverage_io as coverage_io
from unittest.mock import MagicMock
from pathlib import Path

@pytest.fixture
def mock_workspace(tmp_path):
    ws = MagicMock()
    ws.accum = tmp_path / "accum.coverage"
    return ws

@pytest.fixture
def mock_cand_file(tmp_path):
    return tmp_path / "cand.coverage"

def test_characterize_merge_into_accum_valid_input(mock_workspace, mock_cand_file, monkeypatch):
    mock_workspace.accum.touch()  # Create the accumulated file
    mock_cand_file.touch()  # Create the candidate file
    # Mock the CoverageData methods
    mock_coverage_data = MagicMock()
    monkeypatch.setattr("coverage.CoverageData", lambda *args, **kwargs: mock_coverage_data)

    merge_into_accum(mock_workspace, mock_cand_file)
    assert mock_coverage_data.update.call_count == 1  # Ensure update was called

def test_characterize_merge_into_accum_empty_accum(mock_workspace, mock_cand_file, monkeypatch):
    mock_cand_file.touch()  # Create the candidate file
    # Mock the CoverageData methods
    mock_coverage_data = MagicMock()
    monkeypatch.setattr("coverage.CoverageData", lambda *args, **kwargs: mock_coverage_data)

    merge_into_accum(mock_workspace, mock_cand_file)
    assert mock_coverage_data.update.call_count == 1  # Ensure update was called even with empty accum
