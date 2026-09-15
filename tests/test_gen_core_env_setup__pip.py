import pytest
from core.env_setup import _pip
import core.env_setup as env_setup
from pathlib import Path

@pytest.fixture
def mock_log(monkeypatch):
    class MockLog:
        def debug(self, msg, *args):
            pass
    mock_log = MockLog()
    monkeypatch.setattr(env_setup, '_pip', mock_log)  # Patch _pip instead of log
    return mock_log



def test_characterize_pip_invalid_python(mock_log, tmp_path):
    python = "invalid_python"
    args = ["package1"]
    cwd = tmp_path
    with pytest.raises(FileNotFoundError):
        _pip(python, args, cwd, mock_log)
