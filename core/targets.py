"""Phase 2: split source into function-level targets, join with coverage gaps, prioritise.

D1: function granularity. D2: fully-uncovered => function prompt, partial => line-group prompt.
D9: bucket classification is a sorting hint only; the truth comes from running tests.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from .coverage_io import CovState
from .env_setup import Workspace, module_name_for

IO_NAMES = {"open", "input", "print", "exit", "quit"}
IO_MODULES = {
    "os": "filesystem", "sys": "filesystem", "socket": "network", "subprocess": "filesystem",
    "requests": "network", "urllib": "network", "http": "network", "httpx": "network",
    "shutil": "filesystem", "pathlib": "filesystem", "time": "time", "datetime": "time",
    "random": "time", "uuid": "time", "threading": "other", "asyncio": "other",
    "sqlite3": "other", "tempfile": "filesystem", "pickle": "filesystem", "openai": "network",
}
TIME_ATTRS = {"now", "today", "utcnow", "time", "sleep", "monotonic", "perf_counter", "uuid4", "uuid1",
              "random", "randint", "choice", "shuffle", "sample"}
CARD_ORDER = ["time-and-random", "filesystem", "class-and-state", "exception-paths", "patching", "pure-function"]

D_PATTERNS = [
    (re.compile(r"^\s*if\s+__name__"), "main_guard"),
    (re.compile(r"^\s*raise\s+NotImplementedError"), "abstract"),
    (re.compile(r"^\s*\.\.\.\s*$"), "ellipsis"),
    (re.compile(r"^\s*(import|from)\s"), "import"),
    (re.compile(r"^\s*raise\s*$"), "bare_reraise"),
]


@dataclass
class Target:
    file: str                  # repo-relative posix path
    module: str                # dotted import path
    name: str
    qualname: str
    class_name: str | None
    lineno: int
    end: int
    body_lo: int
    src: str                   # function source (with decorators)
    context_before: str
    context_after: str
    missing: list[int]
    executed_in_body: int
    complexity: int
    io_deps: list[str]
    io_kinds: set[str]
    calls_imported: bool
    raises_in_missing: bool
    is_method: bool
    is_async: bool
    is_property: bool
    module_imports: list[str]
    attempts: int = 0
    blacklisted: bool = False
    fail_reasons: list[str] = field(default_factory=list)
    accepted_files: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.file}::{self.qualname}"

    @property
    def fully_uncovered(self) -> bool:
        return self.executed_in_body == 0

    @property
    def is_pure(self) -> bool:
        return not self.io_deps and not self.is_async

    @property
    def priority(self) -> float:
        return len(self.missing) / (1 + 3 * len(self.io_deps) + 0.5 * self.complexity)

    @property
    def missing_groups(self) -> list[tuple[int, int]]:
        out: list[list[int]] = []
        for n in sorted(self.missing):
            if out and n == out[-1][1] + 1:
                out[-1][1] = n
            else:
                out.append([n, n])
        return [tuple(x) for x in out]

    @property
    def import_lines(self) -> list[str]:
        seg = self.module.split(".")[-1]
        alias = seg if seg != self.name else f"{seg}_mod"
        if self.class_name:
            return [f"from {self.module} import {self.class_name}", f"import {self.module} as {alias}"]
        return [f"from {self.module} import {self.name}", f"import {self.module} as {alias}"]

    @property
    def module_alias(self) -> str:
        seg = self.module.split(".")[-1]
        return seg if seg != self.name else f"{seg}_mod"

    def bucket_hint(self) -> str:
        if self.is_async:
            return "B"
        return "A"

    def select_cards(self, mode: str, type_cards: int) -> list[str]:
        cards: list[str] = []
        if mode == "characterize":
            cards.append("characterize")
        typ: list[str] = []
        if "time" in self.io_kinds:
            typ.append("time-and-random")
        if "filesystem" in self.io_kinds or "network" in self.io_kinds:
            typ.append("filesystem")
        if self.is_method:
            typ.append("class-and-state")
        if self.raises_in_missing:
            typ.append("exception-paths")
        if self.calls_imported and "patching" not in typ:
            typ.append("patching")
        if not typ:
            typ.append("pure-function")
        typ.sort(key=CARD_ORDER.index)
        return cards + typ[:max(1, type_cards)]


def _imported_names(tree: ast.Module) -> tuple[set[str], list[str], set[str]]:
    names: set[str] = set()
    lines: list[str] = []
    modules: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for a in node.names:
                top = (a.asname or a.name).split(".")[0]
                names.add(top)
                modules.add(a.name.split(".")[0])
            lines.append(ast.unparse(node))
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                names.add(a.asname or a.name)
            if node.module:
                modules.add(node.module.split(".")[0])
            lines.append(ast.unparse(node))
    return names, lines, modules


def _analyze_function(node, lines, imported: set[str], import_modules: set[str], from_imports: dict[str, str]):
    io: set[str] = set()
    kinds: set[str] = set()
    calls_imported = False
    for x in ast.walk(node):
        if isinstance(x, ast.Call):
            fn = x.func
            if isinstance(fn, ast.Name):
                if fn.id in IO_NAMES:
                    io.add(fn.id)
                    kinds.add("filesystem")
                elif fn.id in imported:
                    calls_imported = True
                    src_mod = from_imports.get(fn.id, "")
                    if src_mod in IO_MODULES:
                        io.add(f"{src_mod}.{fn.id}")
                        kinds.add(IO_MODULES[src_mod])
            elif isinstance(fn, ast.Attribute):
                base = fn.value
                root = base
                while isinstance(root, ast.Attribute):
                    root = root.value
                if isinstance(root, ast.Name):
                    if root.id in IO_MODULES:
                        io.add(f"{root.id}.{fn.attr}")
                        kinds.add(IO_MODULES[root.id])
                        if fn.attr in TIME_ATTRS:
                            kinds.add("time")
                    elif root.id in imported and root.id != "self":
                        calls_imported = True
                if fn.attr in ("write_text", "write_bytes", "unlink", "mkdir", "rmtree", "read_text"):
                    io.add(f"path.{fn.attr}")
                    kinds.add("filesystem")
    complexity = sum(1 for x in ast.walk(node)
                     if isinstance(x, (ast.If, ast.For, ast.While, ast.Try, ast.BoolOp, ast.IfExp, ast.ExceptHandler)))
    return sorted(io), kinds, calls_imported, complexity


def discover(ws: Workspace, cov: CovState, log=None) -> list[Target]:
    root = ws.repo_root
    targets: list[Target] = []
    for rel, missing in cov.missing.items():
        path = root / rel
        if not path.exists():
            continue
        try:
            src = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(src)
        except (SyntaxError, OSError):
            continue
        module = module_name_for(root, Path(rel))
        if module in ws.excluded_modules:
            continue
        lines = src.splitlines()
        imported, import_lines, import_modules = _imported_names(tree)
        from_imports: dict[str, str] = {}
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module:
                for a in node.names:
                    from_imports[a.asname or a.name] = node.module.split(".")[0]
        executed = cov.executed.get(rel, set())

        # map function nodes to class names; skip nested defs (they belong to the parent)
        nested: set[int] = set()
        owners: dict[int, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for ch in ast.walk(node):
                    if ch is not node and isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        nested.add(ch.lineno)
            if isinstance(node, ast.ClassDef):
                for b in node.body:
                    if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        owners[b.lineno] = node.name

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.lineno in nested:
                continue
            end = getattr(node, "end_lineno", node.lineno)
            body_lo = node.body[0].lineno
            span = set(range(body_lo, end + 1))
            miss = sorted(missing & span)
            # drop D-bucket lines from the target (not worth covering)
            miss = [ln for ln in miss if not any(rx.match(lines[ln - 1]) for rx, _ in D_PATTERNS)]
            if not miss:
                continue
            exec_in_body = len(executed & span)
            io, kinds, calls_imported, complexity = _analyze_function(node, lines, imported, import_modules, from_imports)
            raises_in_missing = any(re.match(r"^\s*(raise\b|except\b)", lines[ln - 1]) for ln in miss)
            start = node.decorator_list[0].lineno if node.decorator_list else node.lineno
            is_prop = any(isinstance(d, ast.Name) and d.id == "property" for d in node.decorator_list)
            cls = owners.get(node.lineno)
            targets.append(Target(
                file=rel, module=module, name=node.name,
                qualname=f"{cls}.{node.name}" if cls else node.name, class_name=cls,
                lineno=start, end=end, body_lo=body_lo,
                src="\n".join(lines[start - 1:end]),
                context_before="\n".join(lines[max(0, start - 6):start - 1]),
                context_after="\n".join(lines[end:end + 5]),
                missing=miss, executed_in_body=exec_in_body, complexity=complexity,
                io_deps=io, io_kinds=kinds, calls_imported=calls_imported,
                raises_in_missing=raises_in_missing, is_method=cls is not None,
                is_async=isinstance(node, ast.AsyncFunctionDef), is_property=is_prop,
                module_imports=import_lines,
            ))
    targets.sort(key=lambda t: (not t.is_pure, -t.priority))
    if log:
        pure = sum(1 for t in targets if t.is_pure)
        log.info("targets: %d (pure %d, io-dependent %d), missing lines in targets=%d",
                 len(targets), pure, len(targets) - pure, sum(len(t.missing) for t in targets))
    return targets


def refresh(targets: list[Target], cov: CovState) -> list[Target]:
    """Recompute each target's missing lines after coverage changed; drop finished ones."""
    alive: list[Target] = []
    for t in targets:
        miss = cov.missing.get(t.file, set())
        t.missing = [ln for ln in t.missing if ln in miss]
        if t.missing:
            body = set(range(t.body_lo, t.end + 1))
            t.executed_in_body = len(cov.executed.get(t.file, set()) & body)
            alive.append(t)
    alive.sort(key=lambda t: (not t.is_pure, -t.priority))
    return alive


def numbered(src: str, start: int, highlight: set[int] | None = None) -> str:
    out = []
    for i, ln in enumerate(src.splitlines()):
        n = start + i
        mark = ">>" if highlight and n in highlight else "  "
        out.append(f"{mark}{n:4d}| {ln}")
    return "\n".join(out)
