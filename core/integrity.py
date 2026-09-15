"""SHA-256 manifest of every non-test file. Gate 3: nothing outside tests/ may change."""
from __future__ import annotations

import hashlib
from pathlib import Path

EXCLUDE_DIRS = {
    "tests", "test", ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache",
    "reports", "workspace", "logs", ".mypy_cache", ".ruff_cache", "node_modules",
    "htmlcov", ".hypothesis", ".tox", ".nox", ".eggs", "build", "dist",
}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".log"}
EXCLUDE_PREFIXES = (".coverage",)


def _skip(rel: Path) -> bool:
    parts = rel.parts
    if any(p in EXCLUDE_DIRS or p.endswith(".egg-info") for p in parts[:-1]):
        return True
    name = parts[-1]
    if name.startswith(EXCLUDE_PREFIXES) or name.endswith(tuple(EXCLUDE_SUFFIXES)):
        return True
    if name == "coverage.json":
        return True
    return False


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(root: Path) -> dict[str, str]:
    root = Path(root)
    out: dict[str, str] = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if _skip(rel):
            continue
        try:
            out[rel.as_posix()] = sha256_file(p)
        except OSError:
            continue
    return out


def verify(root: Path, manifest: dict[str, str]) -> list[tuple[str, str]]:
    """Return [(relpath, 'modified'|'added'|'removed')]. Empty list == intact."""
    now = build_manifest(root)
    problems: list[tuple[str, str]] = []
    for k, v in manifest.items():
        if k not in now:
            problems.append((k, "removed"))
        elif now[k] != v:
            problems.append((k, "modified"))
    for k in now:
        if k not in manifest:
            problems.append((k, "added"))
    return sorted(problems)
