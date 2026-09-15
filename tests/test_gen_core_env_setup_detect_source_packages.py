import pytest
from core.env_setup import detect_source_packages
import core.env_setup as env_setup
from pathlib import Path

def test_characterize_detect_source_packages_normal_input(tmp_path):
    # Create a directory structure with Python files
    package_dir = tmp_path / "my_package"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("")
    (package_dir / "module.py").write_text("print('Hello')")
    
    result = detect_source_packages(tmp_path)
    assert result == ['my_package']

def test_characterize_detect_source_packages_empty_input(tmp_path):
    # Test with an empty directory
    result = detect_source_packages(tmp_path)
    assert result == []

def test_characterize_detect_source_packages_no_init_file(tmp_path):
    # Create a directory with a subdirectory without __init__.py
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    package_dir = src_dir / "my_package"
    package_dir.mkdir()
    (package_dir / "module.py").write_text("print('Hello')")
    
    result = detect_source_packages(tmp_path)
    assert result == ['src/my_package']

def test_characterize_detect_source_packages_skip_directories(tmp_path):
    # Create a directory structure with a directory to be skipped
    skip_dir = tmp_path / ".git"
    skip_dir.mkdir()
    
    package_dir = tmp_path / "my_package"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("")
    
    result = detect_source_packages(tmp_path)
    assert result == ['my_package']