import pytest
from core.integrity import verify
import core.integrity as integrity
from pathlib import Path

def test_characterize_verify_normal_input(tmp_path):
    root = tmp_path / "test_root"
    root.mkdir()
    (root / "file1.txt").write_text("content1")
    (root / "file2.txt").write_text("content2")
    
    manifest = {
        "file1.txt": "d41d8cd98f00b204e9800998ecf8427e",  # MD5 hash of empty content
        "file2.txt": "d41d8cd98f00b204e9800998ecf8427e"
    }
    
    result = verify(root, manifest)
    assert result == [('file1.txt', 'modified'), ('file2.txt', 'modified')]

def test_characterize_verify_empty_input(tmp_path):
    root = tmp_path / "empty_root"
    root.mkdir()
    
    manifest = {}
    
    result = verify(root, manifest)
    assert result == []

def test_characterize_verify_removed_file(tmp_path):
    root = tmp_path / "test_root"
    root.mkdir()
    (root / "file1.txt").write_text("content1")
    
    manifest = {
        "file1.txt": "d41d8cd98f00b204e9800998ecf8427e",  # MD5 hash of empty content
        "file2.txt": "d41d8cd98f00b204e9800998ecf8427e"
    }
    
    result = verify(root, manifest)
    assert result == [('file1.txt', 'modified'), ('file2.txt', 'removed')]

def test_characterize_verify_modified_file(tmp_path):
    root = tmp_path / "test_root"
    root.mkdir()
    (root / "file1.txt").write_text("content1")
    
    manifest = {
        "file1.txt": "d41d8cd98f00b204e9800998ecf8427e",  # MD5 hash of empty content
    }
    
    result = verify(root, manifest)
    assert result == [('file1.txt', 'modified')]