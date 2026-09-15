"""characterize mode: `assert <expr> == __CAPTURE__` and `pytest.raises(__CAPTURE_EXC__)` are filled
from one real execution (D4 sentinel mechanism).

Mechanism: __CAPTURE__ is an object whose __eq__ always answers True while recording the other
operand's repr, keyed by the line number of the assert. __CAPTURE_EXC__ blocks are rewritten to a
context manager that swallows and records the exception type. One pytest run collects every value;
the file is then rewritten with the captured literals. Values whose repr does not round-trip
(e.g. <Obj at 0x..>) mark the owning test function for removal.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

SENTINEL_SRC = '''
import sys as _cap_sys, json as _cap_json, atexit as _cap_atexit
_CAP_RESULTS = {}
_CAP_EXC = {}
class _Cap:
    def __eq__(self, other):
        f = _cap_sys._getframe(1)
        _CAP_RESULTS[str(f.f_lineno)] = repr(other)
        return True
    def __ne__(self, other):
        return not self.__eq__(other)
    def __hash__(self):
        return 0
    def __repr__(self):
        return "__CAPTURE__"
__CAPTURE__ = _Cap()
class _CapExc:
    def __init__(self, ln):
        self.ln = ln
    def __enter__(self):
        return self
    def __exit__(self, et, ev, tb):
        if et is None:
            _CAP_EXC[str(self.ln)] = None
        else:
            _CAP_EXC[str(self.ln)] = et.__name__ if et.__module__ == "builtins" else et.__module__ + "." + et.__qualname__
        return True
def __cap_exc(ln):
    return _CapExc(ln)

@_cap_atexit.register
def _cap_dump():
    with open(__CAP_OUT__, "w", encoding="utf-8") as fh:
        _cap_json.dump({"values": _CAP_RESULTS, "exc": _CAP_EXC}, fh)
'''

EXC_RX = re.compile(r"pytest\.raises\(\s*__CAPTURE_EXC__\s*(?:,[^)]*)?\)")
SUSPICIOUS = ("None", "[]", "{}", "''", '""', "()", "set()", "0", "False")


@dataclass
class CharResult:
    ok: bool
    src: str
    dropped: list[str] = field(default_factory=list)       # test functions removed
    problems: list[str] = field(default_factory=list)
    suspicious: list[str] = field(default_factory=list)    # "test_name: value"
    filled: int = 0


def instrument(test_src: str, out_path: str) -> tuple[str, int]:
    header = SENTINEL_SRC.replace("__CAP_OUT__", repr(out_path))
    header_lines = len(header.splitlines()) + 1
    body_lines = []
    for i, ln in enumerate(test_src.splitlines(), 1):
        inst_ln = i + header_lines
        body_lines.append(EXC_RX.sub(f"__cap_exc({inst_ln})", ln))
    return header + "\n" + "\n".join(body_lines), header_lines


def _roundtrip_ok(rep: str) -> bool:
    try:
        ns = {"set": set, "frozenset": frozenset, "inf": float("inf")}
        return repr(eval(rep, {"__builtins__": {}}, ns)) == rep  # noqa: S307 - literal check only
    except Exception:
        return False


def _owner_of_line(tree: ast.Module, lineno: int) -> str | None:
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if n.lineno <= lineno <= getattr(n, "end_lineno", n.lineno):
                return n.name
    return None


def fill(test_src: str, captured: dict, header_lines: int) -> CharResult:
    lines = test_src.splitlines()
    tree = ast.parse(test_src)
    problems: list[str] = []
    suspicious: list[str] = []
    drop: set[str] = set()
    extra_imports: set[str] = set()
    filled = 0

    def mark(idx: int, why: str):
        owner = _owner_of_line(tree, idx + 1)
        problems.append(f"line {idx + 1}: {why}")
        if owner:
            drop.add(owner)

    for ln_str, rep in captured.get("values", {}).items():
        idx = int(ln_str) - header_lines - 1
        if not (0 <= idx < len(lines)) or "__CAPTURE__" not in lines[idx]:
            problems.append(f"line {ln_str}: capture line mapping failed")
            continue
        if not _roundtrip_ok(rep):
            mark(idx, f"repr not reproducible: {rep[:50]}")
            continue
        if rep in SUSPICIOUS:
            owner = _owner_of_line(tree, idx + 1) or "?"
            suspicious.append(f"{owner}: {rep}")
        if rep in ("None", "True", "False"):
            lines[idx] = re.sub(r"==\s*__CAPTURE__", f"is {rep}", lines[idx], count=1)
            lines[idx] = re.sub(r"!=\s*__CAPTURE__", f"is not {rep}", lines[idx], count=1)
        lines[idx] = lines[idx].replace("__CAPTURE__", rep, 1)
        filled += 1

    for ln_str, exc in captured.get("exc", {}).items():
        idx = int(ln_str) - header_lines - 1
        if not (0 <= idx < len(lines)) or "__CAPTURE_EXC__" not in lines[idx]:
            problems.append(f"line {ln_str}: exc capture mapping failed")
            continue
        if exc is None:
            mark(idx, "expected an exception but none was raised")
            continue
        if "." in exc:
            mod = exc.rsplit(".", 1)[0]
            if mod.startswith("_pytest") or mod.startswith("pytest"):
                mark(idx, f"pytest-internal outcome: {exc}")
                continue
            extra_imports.add(f"import {mod}")
        owner = _owner_of_line(tree, idx + 1) or "?"
        suspicious.append(f"{owner}: raises {exc}")
        lines[idx] = lines[idx].replace("__CAPTURE_EXC__", exc, 1)
        filled += 1

    # anything still holding a sentinel was never executed (test failed before reaching it)
    for i, ln in enumerate(lines):
        if "__CAPTURE__" in ln or "__CAPTURE_EXC__" in ln:
            owner = _owner_of_line(tree, i + 1)
            if owner and owner not in drop:
                problems.append(f"line {i + 1}: value never captured")
                drop.add(owner)

    src = "\n".join(lines)
    if re.search(r"\binf\b", src) and "inf = float" not in src:
        src = "inf = float('inf')\n" + src
    if extra_imports:
        src = "\n".join(sorted(extra_imports)) + "\n" + src
    if drop:
        from .validate import strip_functions
        src = strip_functions(src, drop)
    from .validate import test_names
    remaining = test_names(src)
    return CharResult(ok=bool(remaining), src=src, dropped=sorted(drop), problems=problems,
                      suspicious=suspicious, filled=filled)


def characterize(test_path: Path, python: str, cwd: Path, env: dict | None = None,
                 timeout: int = 180, pytest_timeout: int = 30) -> CharResult:
    """Run the sentinel pass on test_path (in place). Returns the filled source (also written)."""
    src = test_path.read_text(encoding="utf-8")
    if "__CAPTURE__" not in src and "__CAPTURE_EXC__" not in src:
        return CharResult(ok=True, src=src)
    out = Path(tempfile.mktemp(suffix=".json", prefix="cap_"))
    inst_path = test_path.with_name(test_path.stem + "_inst.py")
    inst_src, header_lines = instrument(src, str(out))
    inst_path.write_text(inst_src, encoding="utf-8")
    try:
        subprocess.run([python, "-m", "pytest", "-q", str(inst_path), "-p", "no:cacheprovider",
                        "-p", "no:randomly", "--no-header", "-o", "addopts=", f"--timeout={pytest_timeout}",
                        "--rootdir", str(cwd)],
                       cwd=str(cwd), env=env, capture_output=True, timeout=timeout)
        captured = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"values": {}, "exc": {}}
        res = fill(src, captured, header_lines)
        test_path.write_text(res.src, encoding="utf-8")
        return res
    except subprocess.TimeoutExpired:
        return CharResult(ok=False, src=src, problems=["characterize run timed out"])
    finally:
        inst_path.unlink(missing_ok=True)
        out.unlink(missing_ok=True)
