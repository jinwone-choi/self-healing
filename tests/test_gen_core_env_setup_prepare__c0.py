import pytest
from core.env_setup import prepare
import core.env_setup as env_setup
from pathlib import Path

class MockSettings:
    def __init__(self, use_venv=False, repo_branch='main', source_package=None, python_bin='python'):
        self.use_venv = use_venv
        self.repo_branch = repo_branch
        self.source_package = source_package
        self.python_bin = python_bin




def test_characterize_prepare_invalid_repo_path(tmp_path, monkeypatch):
    repo = str(tmp_path / "invalid_repo")
    settings = MockSettings()
    log = lambda x: x  # Mock log function
    
    with pytest.raises(FileNotFoundError):
        prepare(repo, settings, log)
