import pytest
from core.env_setup import Workspace
import core.env_setup as env_setup

def create_workspace():
    return Workspace(
        repo_root="repo_root",
        work_dir="work_dir",
        python="python",
        packages="packages",
        tests_dir="tests_dir",
        rcfile="rcfile",
        cov_dir="cov_dir",
        cand_dir="cand_dir",
        bak_dir="bak_dir",
        accum="accum"
    )

def test_characterize_child_env_normal(monkeypatch):
    monkeypatch.setattr(env_setup, "os", type("os", (object,), {"environ": {}, "pathsep": ":"}))
    workspace = create_workspace()
    result = workspace.child_env()
    assert result == {'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': 'repo_root:'}

def test_characterize_child_env_with_existing_vars(monkeypatch):
    monkeypatch.setattr(env_setup, "os", type("os", (object,), {"environ": {"EXISTING_VAR": "value"}, "pathsep": ":"}))
    workspace = create_workspace()
    result = workspace.child_env()
    assert result == {'EXISTING_VAR': 'value', 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': 'repo_root:'}

def test_characterize_child_env_empty(monkeypatch):
    monkeypatch.setattr(env_setup, "os", type("os", (object,), {"environ": {}, "pathsep": ":"}))
    workspace = create_workspace()
    result = workspace.child_env()
    assert result == {'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': 'repo_root:'}

def test_characterize_child_env_boundary(monkeypatch):
    monkeypatch.setattr(env_setup, "os", type("os", (object,), {"environ": {"COVERAGE_FILE": "some_file"}, "pathsep": ":"}))
    workspace = create_workspace()
    result = workspace.child_env()
    assert result == {'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': 'repo_root:'}