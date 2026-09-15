"""Auto-injected by the coverage agent. Safe to keep.

- puts the repository root on sys.path so `import <package>` works from tests/
- blocks real network sockets (tests must be deterministic and offline)
"""
import os
import socket
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_BLOCK_NETWORK = True


class _NetworkBlocked(RuntimeError):
    pass


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    if not _BLOCK_NETWORK:
        yield
        return

    def _deny(*args, **kwargs):
        raise _NetworkBlocked("network access is blocked in tests")

    monkeypatch.setattr(socket.socket, "connect", _deny)
    monkeypatch.setattr(socket.socket, "connect_ex", _deny)
    monkeypatch.setattr(socket, "create_connection", _deny)
    yield
