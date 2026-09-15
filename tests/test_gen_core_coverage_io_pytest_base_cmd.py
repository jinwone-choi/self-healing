import pytest
from core.coverage_io import pytest_base_cmd
import core.coverage_io as coverage_io
from unittest.mock import MagicMock

@pytest.mark.parametrize("timeout_s", [1, 5, 10])
def test_characterize_pytest_base_cmd_normal_input(timeout_s, tmp_path):
    ws = MagicMock()
    ws.python = "python3"
    ws.repo_root = tmp_path
    result = pytest_base_cmd(ws, timeout_s)
    assert result == ['python3', '-m', 'pytest', '-q', '--no-header', '-p', 'no:cacheprovider', '-p', 'no:randomly', f'--timeout={timeout_s}', '--tb=short', '-rfE', '--color=no', '-o', 'addopts=', '--rootdir', str(tmp_path)]

def test_characterize_pytest_base_cmd_empty_workspace(tmp_path):
    ws = MagicMock()
    ws.python = "python3"
    ws.repo_root = tmp_path
    result = pytest_base_cmd(ws, 0)
    assert result == ['python3', '-m', 'pytest', '-q', '--no-header', '-p', 'no:cacheprovider', '-p', 'no:randomly', '--timeout=0', '--tb=short', '-rfE', '--color=no', '-o', 'addopts=', '--rootdir', str(tmp_path)]