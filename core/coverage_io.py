"""Phase 1/4/5 plumbing: run pytest with coverage, parse coverage.json, accumulate (D5),
parse pytest failures into compact records (L1 input)."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .env_setup import Workspace
from .integrity import sha256_file


@dataclass
class PytestResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode in (0, 5)


@dataclass
class Failure:
    nodeid: str
    test_name: str | None      # None => collection error for the whole file
    exc_type: str
    message: str
    snippet: str = ""

    @property
    def kind(self) -> str:
        m = self.message
        if "DID NOT RAISE" in m:
            return "did_not_raise"
        if self.exc_type.startswith("Timeout") or "Timeout" in m[:40]:
            return "timeout"
        if self.test_name is None:
            return "collection_error"
        if "fixture" in m and "not found" in m:
            return "fixture_not_found"
        if "network access is blocked" in m:
            return "network"
        return self.exc_type or "unknown"


def normalize_key(p: str) -> str:
    return p.replace("\\", "/")


def pytest_base_cmd(ws: Workspace, timeout_s: int) -> list[str]:
    return [ws.python, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider",
            "-p", "no:randomly", f"--timeout={timeout_s}", "--tb=short", "-rfE", "--color=no",
            "-o", "addopts=", "--rootdir", str(ws.repo_root)]


def cov_args(ws: Workspace, json_out: Path | None) -> list[str]:
    args = [f"--cov={p}" for p in ws.packages] + [f"--cov-config={ws.rcfile}"]
    args += ["--cov-report=" + (f"json:{json_out}" if json_out else "")]
    return args


def run_pytest(ws: Workspace, args: list[str], timeout_s: int, cov_file: Path | None,
               wall_timeout: int = 600) -> PytestResult:
    env = ws.child_env()
    if cov_file is not None:
        env["COVERAGE_FILE"] = str(cov_file)
    cmd = pytest_base_cmd(ws, timeout_s) + args
    try:
        r = subprocess.run(cmd, cwd=str(ws.repo_root), env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=wall_timeout)
        return PytestResult(r.returncode, r.stdout or "", r.stderr or "")
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        return PytestResult(124, out, "wall-clock timeout", timed_out=True)


def coverage_json(ws: Workspace, data_file: Path, out_json: Path) -> dict:
    env = ws.child_env()
    cmd = [ws.python, "-m", "coverage", "json", f"--rcfile={ws.rcfile}", f"--data-file={data_file}",
           "-o", str(out_json), "-q"]
    r = subprocess.run(cmd, cwd=str(ws.repo_root), env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    if r.returncode != 0 or not out_json.exists():
        raise RuntimeError(f"coverage json failed: {r.stderr[-400:]}")
    return json.loads(out_json.read_text(encoding="utf-8"))


def ensure_data_file(data_file: Path) -> None:
    """Create an empty-but-valid coverage data file (so reports work with zero tests)."""
    if data_file.exists():
        return
    from coverage import CoverageData
    d = CoverageData(basename=str(data_file))
    d.add_lines({})
    d.write()


@dataclass
class CovState:
    """Line-level accounting derived from coverage.json (statements / missing per file)."""
    statements: dict[str, set[int]] = field(default_factory=dict)
    missing: dict[str, set[int]] = field(default_factory=dict)
    executed: dict[str, set[int]] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict) -> "CovState":
        st = cls()
        for f, info in data.get("files", {}).items():
            k = normalize_key(f)
            ex = set(info.get("executed_lines", []))
            mi = set(info.get("missing_lines", []))
            st.executed[k] = ex
            st.missing[k] = mi
            st.statements[k] = ex | mi
        return st

    @property
    def total(self) -> int:
        return sum(len(v) for v in self.statements.values())

    @property
    def total_missing(self) -> int:
        return sum(len(v) for v in self.missing.values())

    @property
    def percent(self) -> float:
        t = self.total
        return 100.0 if t == 0 else 100.0 * (t - self.total_missing) / t

    def contribution(self, other_executed: dict[str, set[int]]) -> int:
        n = 0
        for f, lines in other_executed.items():
            n += len(lines & self.missing.get(f, set()))
        return n

    def apply(self, other_executed: dict[str, set[int]]) -> int:
        gained = 0
        for f, lines in other_executed.items():
            if f in self.missing:
                hit = lines & self.missing[f]
                gained += len(hit)
                self.missing[f] -= hit
                self.executed.setdefault(f, set()).update(hit)
        return gained


def executed_from_json(data: dict) -> dict[str, set[int]]:
    return {normalize_key(f): set(i.get("executed_lines", [])) for f, i in data.get("files", {}).items()}


def merge_into_accum(ws: Workspace, cand_file: Path) -> None:
    from coverage import CoverageData
    acc = CoverageData(basename=str(ws.accum))
    if ws.accum.exists():
        acc.read()
    other = CoverageData(basename=str(cand_file))
    other.read()
    acc.update(other)
    acc.write()


def backup_accum(ws: Workspace) -> str | None:
    if not ws.accum.exists():
        return None
    shutil.copyfile(ws.accum, ws.bak_dir / "accum_safe.bin")     # outside .coverage.* namespace (D6)
    return sha256_file(ws.accum)


def restore_accum_if_changed(ws: Workspace, before_hash: str | None) -> bool:
    if before_hash is None:
        return False
    if ws.accum.exists() and sha256_file(ws.accum) == before_hash:
        return False
    shutil.copyfile(ws.bak_dir / "accum_safe.bin", ws.accum)
    return True


_SUMMARY_RX = re.compile(r"^(FAILED|ERROR)\s+(\S+?)(?:::(\S+))?(?:\s+-\s+(.*))?$")
_EXC_RX = re.compile(r"^([A-Za-z_][\w.]*?(?:Error|Exception|Exit|Failed|Warning|Timeout|Interrupt))\b")
_ANSI_RX = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_SECTION_RX = re.compile(r"^_{3,}\s+(.+?)\s+_{3,}$")


def parse_failures(out: str) -> list[Failure]:
    out = _ANSI_RX.sub("", out)
    lines = out.splitlines()
    sections: dict[str, list[str]] = {}
    cur: str | None = None
    for ln in lines:
        m = _SECTION_RX.match(ln.strip())
        if m:
            cur = m.group(1).strip()
            sections[cur] = []
            continue
        if ln.startswith("=") or ln.startswith("short test summary"):
            cur = None
            continue
        if cur is not None and len(sections[cur]) < 14:
            sections[cur].append(ln)
    failures: list[Failure] = []
    seen = set()
    for ln in lines:
        m = _SUMMARY_RX.match(ln.strip())
        if not m:
            continue
        status, file_part, test_part, msg = m.groups()
        msg = msg or ""
        test_name = None
        if test_part:
            test_name = test_part.split("[")[0]
        key = (file_part, test_part)
        if key in seen:
            continue
        seen.add(key)
        exc = ""
        mm = re.match(r"^([A-Za-z_][\w.]*?(?:Error|Exception|Exit|Failed|Warning|Timeout|Interrupt))\b", msg)
        if mm:
            exc = mm.group(1).split(".")[-1]
        elif msg.startswith("Failed:"):
            exc = "Failed"
        snippet = ""
        base = test_part.split("[")[0] if test_part else None
        for name, body in sections.items():
            plain = re.sub(r"^ERROR at (setup|teardown) of ", "", name)
            if base and (plain == test_part or plain.startswith(base)):
                snippet = "\n".join(body).strip()
                break
            if test_part is None and "ERROR collecting" in name:
                snippet = "\n".join(body).strip()
                break
        if not msg and snippet:
            # -q hides the reason in the summary line; take the `E   Exc: msg` line of the traceback
            e_lines = [l[4:].strip() for l in snippet.splitlines() if l.startswith("E   ")]
            typed = [l for l in e_lines if _EXC_RX.match(l)]
            if typed or e_lines:
                msg = (typed or e_lines)[-1]
                mm = _EXC_RX.match(msg)
                if mm:
                    exc = mm.group(1).split(".")[-1]
                elif msg.startswith("Failed:"):
                    exc = "Failed"
        failures.append(Failure(nodeid=f"{file_part}::{test_part}" if test_part else file_part,
                                test_name=test_name, exc_type=exc, message=msg[:300], snippet=snippet[:900]))
    return failures


def passed_count(out: str) -> int:
    m = re.search(r"(\d+) passed", _ANSI_RX.sub("", out))
    return int(m.group(1)) if m else 0
