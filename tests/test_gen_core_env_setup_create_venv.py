import pytest
from core.env_setup import create_venv
import core.env_setup as env_setup
from unittest.mock import MagicMock
from pathlib import Path



def test_characterize_create_venv_creation_failure(monkeypatch, tmp_path):
    work_dir = tmp_path
    python_bin = "python3"
    mock_log = MagicMock()
    monkeypatch.setattr(env_setup, 'run', lambda cmd, timeout: MagicMock(returncode=1, stderr="Error"))
    
    with pytest.raises(RuntimeError, match="venv creation failed: Error"):
        create_venv(work_dir, python_bin, mock_log)
