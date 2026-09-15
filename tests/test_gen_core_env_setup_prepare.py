import pytest
from core.env_setup import prepare
import core.env_setup as env_setup
from pathlib import Path



def test_characterize_prepare_non_existent_repo(tmp_path, monkeypatch):
    # Mocking the dependencies
    monkeypatch.setattr(env_setup, "looks_like_url", lambda repo: False)
    monkeypatch.setattr(env_setup, "AGENT_ROOT", tmp_path)
    
    # Create a mock settings object
    class MockSettings:
        use_venv = False
        source_package = None

    mock_settings = MockSettings()
    log = lambda msg: None  # Mock log function

    non_existent_repo_path = tmp_path / "non_existent_repo"

    with pytest.raises(FileNotFoundError):
        prepare(str(non_existent_repo_path), mock_settings, log)
