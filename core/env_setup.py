"""Phase 0: resolve repo (clone or local), interpreter, source packages, coverage rc, conftest.

L2 (environment self-healing): deterministic pip recipes first, then partial progress.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .config import AGENT_ROOT, Settings

SKIP_PKG_DIRS = {
    "tests", "test", "docs", "doc", "examples", "example", "scripts", "benchmarks",
    "workspace", "reports", "logs", "build", "dist", ".git", ".venv", "venv", "env",
    "__pycache__", "node_modules", ".claude", "htmlcov",
}

CONFTEST_TEMPLATE = '''"""Auto-injected by the coverage agent. Safe to keep.

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

_BLOCK_NETWORK = {block_network}


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
'''


@dataclass
class Workspace:
    repo_root: Path
    work_dir: Path
    python: str
    packages: list[str]
    tests_dir: Path
    rcfile: Path
    cov_dir: Path
    cand_dir: Path
    bak_dir: Path
    accum: Path
    is_clone: bool = False
    name: str = ""
    excluded_modules: dict = field(default_factory=dict)   # module -> reason (L2 partial progress)
    env_notes: list = field(default_factory=list)

    def child_env(self) -> dict:
        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(self.repo_root) + os.pathsep + env.get("PYTHONPATH", "")
        env.pop("COVERAGE_FILE", None)
        return env


def looks_like_url(s: str) -> bool:
    return bool(re.match(r"^(https?://|git@|ssh://|git://)", s)) or s.endswith(".git")


def run(cmd: list[str], cwd: Path | None = None, env: dict | None = None, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=timeout)


def clone_repo(url: str, dest: Path, branch: str, log) -> Path:
    if dest.exists():
        log.info("workspace exists, reusing clone: %s", dest)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd += ["--branch", branch]
    cmd += [url, str(dest)]
    log.info("git clone %s", url)
    r = run(cmd, timeout=900)
    if r.returncode != 0:
        raise RuntimeError(f"git clone failed: {r.stderr[-800:]}")
    return dest


def detect_source_packages(root: Path) -> list[str]:
    """Top-level importable packages (dirs with .py files), src/ layout aware."""
    candidates: list[str] = []
    search_roots = [root]
    src = root / "src"
    if src.is_dir() and not (src / "__init__.py").exists():
        search_roots.insert(0, src)
    for base in search_roots:
        for d in sorted(base.iterdir()):
            if not d.is_dir() or d.name in SKIP_PKG_DIRS or d.name.startswith("."):
                continue
            if any(d.glob("*.py")) or (d / "__init__.py").exists():
                rel = d.relative_to(root).as_posix()
                candidates.append(rel)
        if candidates:
            break
    return candidates


def _pip(python: str, args: list[str], cwd: Path, log, timeout: int = 900) -> subprocess.CompletedProcess:
    cmd = [python, "-m", "pip", "install", "--disable-pip-version-check", "-q"] + args
    log.debug("pip: %s", " ".join(args))
    return run(cmd, cwd=cwd, timeout=timeout)


def pip_install_with_recipes(python: str, req_file: Path, cwd: Path, log) -> tuple[bool, list[str]]:
    """L2 deterministic recipes. Returns (all_ok, failed_packages)."""
    r = _pip(python, ["-r", str(req_file)], cwd, log)
    if r.returncode == 0:
        return True, []
    err = (r.stderr or "") + (r.stdout or "")
    log.warning("L2: requirements install failed, applying recipes. tail=%s", err[-400:].replace("\n", " | "))
    if re.search(r"(Failed building wheel|error: subprocess-exited|Microsoft Visual C\+\+|gcc)", err):
        r = _pip(python, ["--only-binary=:all:", "-r", str(req_file)], cwd, log)
        if r.returncode == 0:
            log.info("L2 recipe worked: --only-binary=:all:")
            return True, []
    # per-line install, skip what fails (partial progress)
    failed: list[str] = []
    for line in req_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        r = _pip(python, [line], cwd, log)
        if r.returncode != 0:
            r2 = _pip(python, ["--no-deps", line], cwd, log)
            if r2.returncode != 0:
                failed.append(line)
                log.warning("L2: could not install %s (skipping)", line)
    return not failed, failed


def create_venv(work_dir: Path, python_bin: str, log) -> str:
    venv = work_dir / ".venv"
    py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not py.exists():
        log.info("creating venv at %s", venv)
        r = run([python_bin, "-m", "venv", str(venv)], timeout=300)
        if r.returncode != 0:
            raise RuntimeError(f"venv creation failed: {r.stderr[-500:]}")
    return str(py)


def write_rcfile(path: Path, packages: list[str]) -> None:
    src = ",".join(packages)
    path.write_text(
        "[run]\n"
        f"source = {src}\n"
        "branch = False\n"
        "omit =\n    */tests/*\n    */conftest.py\n    */setup.py\n"
        "[report]\n"
        "exclude_lines =\n"
        "    pragma: no cover\n"
        "    if __name__ == .__main__.:\n"
        "    if TYPE_CHECKING:\n"
        "    if t\\.TYPE_CHECKING:\n"
        "    @(abc\\.)?abstractmethod\n"
        "    ^\\s*\\.\\.\\.\\s*$\n"
        "    raise NotImplementedError\n",
        encoding="utf-8",
    )


def ensure_conftest(tests_dir: Path, block_network: bool, log) -> None:
    tests_dir.mkdir(parents=True, exist_ok=True)
    conftest = tests_dir / "conftest.py"
    if conftest.exists():
        log.info("tests/conftest.py already exists, leaving it untouched")
        return
    conftest.write_text(CONFTEST_TEMPLATE.replace("{block_network}", "True" if block_network else "False"),
                        encoding="utf-8")
    log.info("injected tests/conftest.py (sys.path + network block=%s)", block_network)


def module_name_for(repo_root: Path, rel: Path) -> str:
    parts = list(rel.with_suffix("").parts)
    if parts and parts[0] == "src" and not (repo_root / "src" / "__init__.py").exists():
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def prepare(repo: str, settings: Settings, log) -> Workspace:
    is_clone = looks_like_url(repo)
    if is_clone:
        name = re.sub(r"\.git$", "", repo.rstrip("/").split("/")[-1]) or "repo"
        work_dir = AGENT_ROOT / "workspace" / name
        repo_root = clone_repo(repo, work_dir / "repo", settings.repo_branch, log)
    else:
        repo_root = Path(repo).expanduser().resolve()
        if not repo_root.is_dir():
            raise FileNotFoundError(f"repo path not found: {repo_root}")
        name = repo_root.name
        work_dir = AGENT_ROOT / "workspace" / name
    work_dir.mkdir(parents=True, exist_ok=True)
    cov_dir, cand_dir, bak_dir = work_dir / "cov", work_dir / "cand", work_dir / "bak"
    for d in (cov_dir, cand_dir, bak_dir):
        d.mkdir(exist_ok=True)
    # a fresh run starts from a clean accumulator
    for stale in list(cov_dir.glob("*")) + list(cand_dir.glob("*")):
        try:
            stale.unlink()
        except OSError:
            pass

    # interpreter
    use_venv = settings.use_venv or is_clone
    if use_venv:
        python = create_venv(work_dir, settings.python_bin, log)
    else:
        python = sys.executable
        log.info("using current interpreter in-place: %s", python)

    ws = Workspace(repo_root=repo_root, work_dir=work_dir, python=python, packages=[],
                   tests_dir=repo_root / "tests", rcfile=work_dir / "coveragerc",
                   cov_dir=cov_dir, cand_dir=cand_dir, bak_dir=bak_dir,
                   accum=cov_dir / "accum.bin", is_clone=is_clone, name=name)

    # dependencies (L2)
    req = repo_root / "requirements.txt"
    if use_venv:
        if req.exists():
            ok, failed = pip_install_with_recipes(python, req, repo_root, log)
            if failed:
                ws.env_notes.append(f"requirements not installed (partial progress): {failed}")
        for proj in ("pyproject.toml", "setup.py"):
            if (repo_root / proj).exists():
                r = _pip(python, ["-e", "."], repo_root, log)
                if r.returncode != 0:
                    ws.env_notes.append(f"pip install -e . failed: {r.stderr[-200:]}")
                break
    r = run([python, "-c", "import pytest, pytest_cov, pytest_timeout, coverage"], cwd=repo_root)
    if r.returncode != 0:
        log.info("installing pytest, pytest-cov, pytest-timeout, coverage")
        r = _pip(python, ["pytest", "pytest-cov", "pytest-timeout", "coverage"], repo_root, log)
        if r.returncode != 0:
            raise RuntimeError(f"cannot install test tooling: {r.stderr[-500:]}")

    # packages
    if settings.source_package:
        ws.packages = [p.strip() for p in settings.source_package.split(",") if p.strip()]
    else:
        ws.packages = detect_source_packages(repo_root)
    if not ws.packages:
        raise RuntimeError("no source package detected; set SOURCE_PACKAGE")
    log.info("coverage source packages: %s", ws.packages)

    # L2 partial progress: modules that fail to import are excluded from targeting
    for pkg in ws.packages:
        pkg_dir = repo_root / pkg
        for py in sorted(pkg_dir.rglob("*.py")):
            rel = py.relative_to(repo_root)
            if any(part in ("tests", "test") for part in rel.parts):
                continue
            mod = module_name_for(repo_root, rel)
            chk = run([python, "-c", f"import {mod}"], cwd=repo_root, env=ws.child_env(), timeout=60)
            if chk.returncode != 0:
                last = (chk.stderr.strip().splitlines() or ["?"])[-1]
                ws.excluded_modules[mod] = last[:200]
                log.warning("L2: module %s not importable, excluded from targets: %s", mod, last[:120])

    write_rcfile(ws.rcfile, ws.packages)
    ensure_conftest(ws.tests_dir, settings.block_network, log)
    return ws
