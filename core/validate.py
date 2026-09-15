"""Phase 4 gate 1 + L0: turn raw model output into a static-safe test module (no LLM calls).

L0 (generation self-healing): fence extraction, parse repair by truncation, import injection,
duplicate test names, `is __CAPTURE__` -> `== __CAPTURE__`.
Gate 1 (static): test functions exist, each has an assert, no forbidden calls, no literal-path writes.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field

from .targets import Target

FENCE_RX = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)

FORBIDDEN_CALLS = {
    ("subprocess", "run"), ("subprocess", "Popen"), ("subprocess", "call"),
    ("subprocess", "check_call"), ("subprocess", "check_output"),
    ("os", "system"), ("os", "remove"), ("os", "unlink"), ("os", "rmdir"), ("os", "removedirs"),
    ("os", "rename"), ("os", "replace"), ("os", "_exit"), ("os", "kill"), ("os", "execv"),
    ("shutil", "rmtree"), ("shutil", "move"), ("sys", "exit"),
    ("socket", "socket"), ("socket", "create_connection"),
    ("requests", "get"), ("requests", "post"), ("urllib", "urlopen"),
}
FORBIDDEN_NAMES = {"exit", "quit", "breakpoint"}
FORBIDDEN_IMPORT_FROM = {"subprocess", "socket"}


@dataclass
class Normalized:
    src: str
    fixes: list[str] = field(default_factory=list)
    ok: bool = True
    reason: str = ""


def _parses_with_test(code: str) -> bool:
    try:
        return any(n.name.startswith("test") for n in ast.parse(code).body
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
    except SyntaxError:
        return False


def extract_code(text: str) -> str | None:
    # outermost fence first: tolerates ``` inside string literals of the tests
    m_open = re.search(r"```(?:python|py)?[ \t]*\n", text)
    if m_open:
        close = text.rfind("```")
        if close > m_open.end():
            outer = text[m_open.end():close].strip("\n")
            if _parses_with_test(outer):
                return outer
    blocks = FENCE_RX.findall(text)
    if blocks:
        # take the largest block that looks like a test module
        blocks.sort(key=len, reverse=True)
        for b in blocks:
            if "def test_" in b:
                return b.strip("\n")
        return blocks[0].strip("\n")
    if "def test_" in text:
        lines = text.splitlines()
        start = 0
        for i, ln in enumerate(lines):
            if ln.startswith(("import ", "from ", "def ", "@", "class ")):
                start = i
                break
        return "\n".join(lines[start:]).strip("\n")
    return None


def parse_or_truncate(src: str, max_cut: int = 60) -> tuple[ast.Module | None, str, bool]:
    """Try ast.parse; on failure cut trailing lines (an unfinished last function) until it parses."""
    try:
        return ast.parse(src), src, False
    except SyntaxError:
        pass
    lines = src.splitlines()
    for cut in range(1, min(max_cut, len(lines))):
        cand = "\n".join(lines[:-cut])
        try:
            tree = ast.parse(cand)
            if any(isinstance(n, ast.FunctionDef) and n.name.startswith("test") for n in tree.body):
                return tree, cand, True
        except SyntaxError:
            continue
    return None, src, False


def test_functions(tree: ast.Module) -> list[ast.FunctionDef]:
    return [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test")]


def _has_assert(fn: ast.AST) -> bool:
    for x in ast.walk(fn):
        if isinstance(x, ast.Assert):
            if isinstance(x.test, ast.Constant):
                continue          # assert True / assert 1 -> not a real assertion
            return True
        if isinstance(x, ast.With):
            for item in x.items:
                c = item.context_expr
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "raises":
                    return True
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "__cap_exc":
                    return True
        if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and x.func.attr == "raises":
            return True
    return False


def _forbidden(tree: ast.Module) -> str | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] in FORBIDDEN_IMPORT_FROM:
            return f"import from {node.module}"
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name):
                if fn.id in FORBIDDEN_NAMES:
                    return f"call {fn.id}()"
                if fn.id == "open":
                    # open("literal", "w") is a write outside tmp_path
                    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        mode = ""
                        if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                            mode = str(node.args[1].value)
                        for kw in node.keywords:
                            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                                mode = str(kw.value.value)
                        if any(ch in mode for ch in "wax+"):
                            return "open() write with literal path"
            elif isinstance(fn, ast.Attribute):
                root = fn.value
                if isinstance(root, ast.Name) and (root.id, fn.attr) in FORBIDDEN_CALLS:
                    return f"call {root.id}.{fn.attr}()"
                if fn.attr in ("write_text", "write_bytes", "unlink", "rmdir") and isinstance(root, ast.Call):
                    # Path("literal").write_text(...) -> writing to a fixed path
                    if isinstance(root.func, ast.Name) and root.func.id == "Path" and root.args \
                            and isinstance(root.args[0], ast.Constant):
                        return "Path(literal).write/unlink"
    return None


def normalize(raw: str, target: Target, mode: str) -> Normalized:
    """L0: raw model output -> parsable module with correct imports. Never calls the LLM."""
    fixes: list[str] = []
    code = extract_code(raw)
    if code is None:
        return Normalized("", fixes, False, "no_code")
    if not FENCE_RX.search(raw):
        fixes.append("no_fence_sliced")
    if "```" in code:
        code = code.replace("```", "")
        fixes.append("stray_fence_removed")

    if mode == "characterize":
        new = re.sub(r"\bis\s+__CAPTURE__", "== __CAPTURE__", code)
        new = re.sub(r"\bis\s+not\s+__CAPTURE__", "!= __CAPTURE__", new)
        if new != code:
            fixes.append("is_capture_to_eq")
            code = new

    tree, code, truncated = parse_or_truncate(code)
    if tree is None:
        return Normalized(code, fixes, False, "syntax_error")
    if truncated:
        fixes.append("truncated_unfinished_tail")

    # import injection: the exact lines the prompt gave
    have = code
    needed = ["import pytest"] + target.import_lines
    missing = [ln for ln in needed if ln not in have and not _import_covered(tree, ln)]
    if missing:
        code = "\n".join(missing) + "\n" + code
        fixes.append("imports_injected:" + ",".join(m.split(" import ")[-1] for m in missing))
        tree = ast.parse(code)

    # duplicate test names
    seen: dict[str, int] = {}
    renames: list[tuple[ast.FunctionDef, str]] = []
    for fn in test_functions(tree):
        if fn.name in seen:
            seen[fn.name] += 1
            renames.append((fn, f"{fn.name}_{seen[fn.name]}"))
        else:
            seen[fn.name] = 0
    if renames:
        lines = code.splitlines()
        for fn, new in renames:
            lines[fn.lineno - 1] = lines[fn.lineno - 1].replace(f"def {fn.name}(", f"def {new}(", 1)
        code = "\n".join(lines)
        fixes.append("dedup_names")
    return Normalized(code, fixes, True, "")


def _import_covered(tree: ast.Module, line: str) -> bool:
    """`from m import x` is covered if x is imported from m under any alias; `import m as a` if m imported."""
    m = re.match(r"from (\S+) import (\S+)", line)
    if m:
        mod, name = m.groups()
        for n in tree.body:
            if isinstance(n, ast.ImportFrom) and n.module == mod and any(a.name == name for a in n.names):
                return True
        return False
    m = re.match(r"import (\S+)(?: as (\S+))?", line)
    if m:
        mod = m.group(1)
        for n in tree.body:
            if isinstance(n, ast.Import) and any(a.name == mod for a in n.names):
                return True
    return False


def static_gate(src: str) -> tuple[bool, str, list[str]]:
    """Returns (ok, reason, assertless_test_names)."""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return False, f"syntax_error:{e.msg}", []
    fns = test_functions(tree)
    if not fns:
        return False, "no_test_function", []
    bad = _forbidden(tree)
    if bad:
        return False, "forbidden:" + bad, []
    assertless = [fn.name for fn in fns if not _has_assert(fn)]
    if len(assertless) == len(fns):
        return False, "no_assert", assertless
    return True, "", assertless


def strip_functions(src: str, names: set[str]) -> str:
    """Remove top-level functions by name (AST line ranges). Keeps everything else."""
    if not names:
        return src
    tree = ast.parse(src)
    lines = src.splitlines()
    drop: set[int] = set()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names:
            start = n.decorator_list[0].lineno if n.decorator_list else n.lineno
            drop.update(range(start, getattr(n, "end_lineno", n.lineno) + 1))
    kept = [ln for i, ln in enumerate(lines, 1) if i not in drop]
    return "\n".join(kept).rstrip() + "\n"


def test_names(src: str) -> list[str]:
    try:
        return [fn.name for fn in test_functions(ast.parse(src))]
    except SyntaxError:
        return []


def count_asserts(src: str) -> tuple[int, int]:
    """(test functions, assert statements) for the assertion-density metric."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return 0, 0
    fns = test_functions(tree)
    n_assert = sum(1 for fn in fns for x in ast.walk(fn) if isinstance(x, ast.Assert))
    n_raises = sum(1 for fn in fns for x in ast.walk(fn)
                   if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and x.func.attr == "raises")
    return len(fns), n_assert + n_raises
