import pytest
from core.env_setup import looks_like_url
import core.env_setup as env_setup

def test_characterize_looks_like_url_normal_input():
    result = looks_like_url("https://example.com")
    assert result is True

def test_characterize_looks_like_url_git_input():
    result = looks_like_url("git@github.com:user/repo.git")
    assert result is True

def test_characterize_looks_like_url_empty_input():
    result = looks_like_url("")
    assert result is False

def test_characterize_looks_like_url_invalid_input():
    result = looks_like_url("invalid_url")
    assert result is False