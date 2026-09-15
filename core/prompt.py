"""Phase 3: prompt assembly. Code computes everything (imports, gaps, cards); the LLM only writes tests.

Rule cards live in .claude/skills/pytest-authoring/rules and are injected 1-2 at a time.
"""
from __future__ import annotations

from pathlib import Path

from .config import AGENT_ROOT
from .coverage_io import Failure
from .targets import Target, numbered

RULES_DIR = AGENT_ROOT / ".claude" / "skills" / "pytest-authoring" / "rules"

SYSTEM_GEN = (
    "You write pytest unit tests for one Python function. "
    "Output exactly ONE ```python code block containing a complete test module and nothing else. "
    "No prose before or after the block. Every test function must contain at least one assert "
    "(or a pytest.raises block). Never write files outside tmp_path, never use the network, "
    "never call subprocess or os.system. Tests must be deterministic."
)

SYSTEM_REPAIR = (
    "You fix a failing pytest module. Output exactly ONE ```python code block with the full corrected "
    "module and nothing else. Keep tests that already pass unchanged. Remove a test only if it cannot "
    "be fixed. Every test must keep at least one assert."
)


def estimate_tokens(s: str) -> int:
    # conservative: non-ASCII (Korean cards) counts ~1 token per char
    ascii_chars = sum(1 for c in s if ord(c) < 128)
    return ascii_chars // 4 + (len(s) - ascii_chars)


def load_card(name: str) -> str:
    p = RULES_DIR / f"{name}.md"
    return p.read_text(encoding="utf-8").strip() if p.exists() else ""


def find_fewshot(tests_dir: Path, max_lines: int = 40) -> str | None:
    """A short existing test from the same repo (style few-shot). Prefer human-written files."""
    if not tests_dir.exists():
        return None
    files = sorted(tests_dir.rglob("test_*.py"))
    human = [f for f in files if not f.name.startswith("test_gen_")]
    for f in human + [f for f in files if f.name.startswith("test_gen_")]:
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        if 5 <= len(lines) <= max_lines and any(l.startswith("def test_") for l in lines):
            return "\n".join(lines)
    return None


def _target_block(t: Target) -> str:
    head = f"File: {t.file}\nModule import path: {t.module}\n"
    if t.class_name:
        head += f"Method: {t.class_name}.{t.name}\n"
    else:
        head += f"Function: {t.name}\n"
    imports = "\n".join(["import pytest"] + t.import_lines)
    head += f"\nUse exactly these imports (do not invent others for the target):\n```python\n{imports}\n```\n"
    if t.calls_imported or t.io_deps:
        head += (f"To monkeypatch names the function uses, patch them on the module object "
                 f"`{t.module_alias}` (e.g. monkeypatch.setattr({t.module_alias}, \"name\", fake)).\n")
    return head


def _gap_block(t: Target) -> str:
    miss = set(t.missing)
    if t.fully_uncovered:
        intro = "This function has never been executed by any test. Write tests that call it."
    else:
        groups = ", ".join(f"{a}" if a == b else f"{a}-{b}" for a, b in t.missing_groups)
        intro = (f"This function is partially covered. The lines marked with >> (lines {groups}) "
                 f"have NOT been executed yet. Choose inputs that make execution reach those lines.")
    return intro + "\n"


def build_generation_prompt(t: Target, mode: str, cards: list[str], fewshot: str | None,
                            max_context_tokens: int, module_deps_max: int = 12,
                            extra_instruction: str = "") -> tuple[str, str]:
    imports_of_module = "\n".join(t.module_imports[:module_deps_max])
    miss = set(t.missing)
    source = numbered(t.src, t.lineno, miss)
    ctx_before = numbered(t.context_before, t.lineno - len(t.context_before.splitlines())) if t.context_before else ""
    ctx_after = numbered(t.context_after, t.end + 1) if t.context_after else ""

    n_tests = "2-4"
    naming = "test_characterize_" if mode == "characterize" else "test_"
    task = (f"\nWrite {n_tests} test functions (names start with `{naming}`). "
            "Cover distinct paths: a normal input, a boundary/empty input, and the marked lines. ")
    if mode == "characterize":
        task += ("Do NOT predict return values: write `assert <expr> == __CAPTURE__` and the harness fills "
                 "the value. For expected exceptions write `with pytest.raises(__CAPTURE_EXC__):`. "
                 "Use `==` with __CAPTURE__ only (never `is`, `in`, or `<`). "
                 "Capture only plain values (numbers, strings, bools, None, lists, dicts, tuples, sets): "
                 "for objects/dataclasses/paths assert on attributes or str(...) "
                 "(e.g. `assert result.name == __CAPTURE__`), never on the whole object. ")
    else:
        task += "Write concrete expected values. "
    task += "Use tmp_path for any file, monkeypatch for any dependency. No network."
    if extra_instruction:
        task += "\n" + extra_instruction

    parts_fixed = [
        "## Target\n" + _target_block(t),
        "## Coverage gap\n" + _gap_block(t),
        "## Source (>> = not yet executed)\n```python\n" + "\n".join(x for x in (ctx_before, source, ctx_after) if x) + "\n```\n",
        "## Imports at the top of the target module\n```python\n" + imports_of_module + "\n```\n",
    ]
    card_text = ["## Rule: " + c + "\n" + load_card(c) + "\n" for c in cards]
    fs = ("## Style example from this repository\n```python\n" + fewshot + "\n```\n") if fewshot else ""

    def assemble(cards_used, fs_used, ctx_used):
        p = list(parts_fixed)
        if not ctx_used:
            p[2] = "## Source (>> = not yet executed)\n```python\n" + source + "\n```\n"
        return "\n".join(p + cards_used + ([fs_used] if fs_used else [])) + task

    # trim to budget: drop few-shot, then extra cards, then context lines
    user = assemble(card_text, fs, True)
    if estimate_tokens(user) > max_context_tokens:
        user = assemble(card_text, "", True)
    if estimate_tokens(user) > max_context_tokens and len(card_text) > 1:
        user = assemble(card_text[:1], "", True)
    if estimate_tokens(user) > max_context_tokens:
        user = assemble(card_text[:1], "", False)
    return SYSTEM_GEN, user


def compact_failures(failures: list[Failure], limit: int = 4) -> str:
    out = []
    for f in failures[:limit]:
        name = f.test_name or "(collection)"
        out.append(f"- {name}: {f.exc_type or f.kind}: {f.message[:200]}")
        if f.snippet:
            snip = "\n".join(f.snippet.splitlines()[-6:])
            out.append("```\n" + snip + "\n```")
    return "\n".join(out)


def build_repair_prompt(t: Target, test_src: str, failures: list[Failure], mode: str,
                        card: str | None = None) -> tuple[str, str]:
    user = ("## Failing test module\n```python\n" + test_src + "\n```\n\n"
            "## Failures (compact)\n" + compact_failures(failures) + "\n\n"
            "## Target source\n```python\n" + numbered(t.src, t.lineno, set(t.missing)) + "\n```\n"
            + "Use exactly these imports: " + "; ".join(t.import_lines) + "\n")
    if card:
        user += "\n## Rule: " + card + "\n" + load_card(card) + "\n"
    if mode == "characterize":
        user += ("\nKeep `== __CAPTURE__` / `pytest.raises(__CAPTURE_EXC__)` placeholders for values you "
                 "are not sure about; the harness fills them.\n")
    user += "\nReturn the full corrected module in one ```python block."
    return SYSTEM_REPAIR, user
