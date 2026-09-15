import pytest
from core.env_setup import module_name_for
import core.env_setup as env_setup
from pathlib import Path

def test_characterize_module_name_for_normal_input(tmp_path):
    repo_root = tmp_path
    rel = Path("src/module/__init__.py")
    result = module_name_for(repo_root, rel)
    assert result == 'module'


def test_characterize_module_name_for_boundary_input(tmp_path):
    repo_root = tmp_path
    rel = Path("src/module")
    result = module_name_for(repo_root, rel)
    assert result == 'module'

def test_characterize_module_name_for_no_init_file(tmp_path):
    repo_root = tmp_path
    (repo_root / "src").mkdir()
    rel = Path("src/module/__init__.py")
    result = module_name_for(repo_root, rel)
    assert result == 'module'
