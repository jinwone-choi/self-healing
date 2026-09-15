"""Orchestration: baseline -> targets -> (generate -> gate -> characterize -> isolated run -> repair)
-> accept/rollback -> escalation ladder -> suite healing -> hard gate.

Everything here is deterministic Python. The LLM is called only inside `_generate` and `_repair`.
"""
from __future__ import annotations

import re
import shutil
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from . import characterize as charmod
from . import coverage_io as cio
from . import integrity, prompt, targets as tmod, validate
from .config import Settings
from .coverage_io import CovState, Failure
from .env_setup import Workspace
from .llm import LLM, BudgetExceeded
from .targets import Target


class IntegrityViolation(RuntimeError):
    pass


@dataclass
class Eval:
    passed: bool
    src: str
    gained: int = 0
    executed: dict = field(default_factory=dict)
    cand_path: Path | None = None
    cand_bin: Path | None = None
    failures: list[Failure] = field(default_factory=list)
    reason: str = ""
    n_llm_repairs: int = 0
    n_prunes: int = 0
    char: charmod.CharResult | None = None


@dataclass
class Accepted:
    target: str
    file: str
    tests: int
    asserts: int
    characterized: int
    gained: int
    percent_after: float
    suspicious: list[str]
    level: str
    llm_repairs: int
    prunes: int


def _safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


class Pipeline:
    def __init__(self, ws: Workspace, settings: Settings, log, events, llm: LLM, run_id: str):
        self.ws, self.s, self.log, self.events, self.llm, self.run_id = ws, settings, log, events, llm, run_id
        self.t0 = time.time()
        self.manifest: dict[str, str] = {}
        self.cov: CovState | None = None
        self.baseline_percent = 0.0
        self.baseline_json: dict = {}
        self.targets: list[Target] = []
        self.known_failures: list[Failure] = []
        self.accepted: list[Accepted] = []
        self.rejected: list[dict] = []
        self.healing: Counter = Counter()
        self.level = "S0"
        self.max_level = "S0"
        self.n_candidates = settings.candidates
        self.type_cards = 1
        self.stop_reason = ""
        self.final_percent: float | None = None
        self.gate_passed = False
        self.suite_notes: list[str] = []
        self.integrity_alerts: list[str] = []

    # ------------------------------------------------------------------ helpers
    def _elapsed_min(self) -> float:
        return (time.time() - self.t0) / 60.0

    def _budget_ok(self) -> bool:
        if self._elapsed_min() > self.s.max_runtime_minutes:
            self.stop_reason = f"runtime budget exceeded ({self.s.max_runtime_minutes} min)"
            return False
        if self.llm.calls >= self.s.max_llm_calls:
            self.stop_reason = f"LLM call budget exceeded ({self.s.max_llm_calls})"
            return False
        return True

    def _deselect_args(self) -> list[str]:
        args: list[str] = []
        for f in self.known_failures:
            if f.test_name is None:
                args += ["--ignore", f.nodeid]
            else:
                args += ["--deselect", f.nodeid]
        return args

    def _snapshot(self) -> None:
        """Copy every manifest file so a violated workspace can be restored (git-less repos too)."""
        snap = self.ws.bak_dir / "snapshot"
        shutil.rmtree(snap, ignore_errors=True)
        for rel in self.manifest:
            dst = snap / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.ws.repo_root / rel, dst)

    def _restore(self, problems: list[tuple[str, str]]) -> None:
        snap = self.ws.bak_dir / "snapshot"
        for rel, kind in problems:
            target = self.ws.repo_root / rel
            if kind == "added":
                try:
                    target.unlink()
                    self.log.warning("    integrity: deleted stray file %s", rel)
                except OSError as e:
                    self.log.error("    integrity: could not delete %s: %s", rel, e)
            else:
                src = snap / rel
                if src.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, target)
                    self.log.warning("    integrity: restored %s from snapshot (%s)", rel, kind)

    def _check_integrity(self, context: str) -> bool:
        """Gate 3. Returns True when a violation was found (and repaired). Raises when configured to stop."""
        problems = integrity.verify(self.ws.repo_root, self.manifest)
        if not problems:
            return False
        msg = f"INTEGRITY VIOLATION during {context}: " + ", ".join(f"{p}({k})" for p, k in problems[:8])
        self.log.error(msg)
        self.integrity_alerts.append(msg)
        self.events.emit("integrity_violation", context=context, problems=problems)
        self._restore(problems)
        still = integrity.verify(self.ws.repo_root, self.manifest)
        if still:
            raise IntegrityViolation(msg + " (could not restore: " + str(still[:4]) + ")")
        if self.s.fail_on_integrity:
            raise IntegrityViolation(msg)
        return True

    # ------------------------------------------------------------------ phase 1
    def baseline(self) -> None:
        ws = self.ws
        self.manifest = integrity.build_manifest(ws.repo_root)
        self.log.info("integrity manifest: %d non-test files hashed", len(self.manifest))
        bjson = ws.cov_dir / "baseline.json"
        has_tests = any(ws.tests_dir.rglob("test_*.py"))
        if not has_tests:
            self.log.info("no existing tests found; baseline is measured from an empty run")
        # always run pytest (even with zero tests) so coverage records the unexecuted source files
        r = cio.run_pytest(ws, ["tests"] + cio.cov_args(ws, bjson), self.s.pytest_timeout_s, ws.accum, wall_timeout=1800)
        self.known_failures = cio.parse_failures(r.stdout)
        if self.known_failures:
            self.log.warning("baseline: %d pre-existing failing tests are recorded and deselected (not fixed)",
                             len(self.known_failures))
            for f in self.known_failures:
                self.log.info("  known failure: %s - %s", f.nodeid, f.message[:100])
            ws.accum.unlink(missing_ok=True)
            r = cio.run_pytest(ws, ["tests"] + self._deselect_args() + cio.cov_args(ws, bjson),
                               self.s.pytest_timeout_s, ws.accum, wall_timeout=1800)
        if r.returncode not in (0, 1, 5):
            self.log.error("baseline pytest returned %d:\n%s", r.returncode, r.stdout[-1500:])
            raise RuntimeError("baseline test run could not complete (collection error?)")
        if not ws.accum.exists():
            self.log.error("pytest output:\n%s", r.stdout[-1500:])
            raise RuntimeError("coverage data file was not produced by the baseline run")
        data = cio.coverage_json(ws, ws.accum, bjson)
        self.baseline_json = data
        self.cov = CovState.from_json(data)
        self.baseline_percent = self.cov.percent
        self._check_integrity("baseline")
        self._snapshot()
        self.log.info("BASELINE coverage %.2f%% (%d statements, %d missing) target=%.0f%%",
                      self.baseline_percent, self.cov.total, self.cov.total_missing, self.s.target_coverage)
        self.events.emit("baseline", percent=round(self.baseline_percent, 2), statements=self.cov.total,
                         missing=self.cov.total_missing, known_failures=len(self.known_failures))

    # ------------------------------------------------------------------ phase 2
    def discover_targets(self) -> None:
        self.targets = tmod.discover(self.ws, self.cov, self.log)
        for t in self.targets[:15]:
            self.log.info("  target %-45s miss=%3d %s prio=%.1f cards=%s", t.key, len(t.missing),
                          "FULL" if t.fully_uncovered else "part", t.priority,
                          t.select_cards(self.s.mode, self.type_cards))

    def _next_target(self) -> Target | None:
        for t in self.targets:
            if t.blacklisted or t.attempts >= self.s.max_attempts_per_target:
                continue
            if t.attempts == 0 or getattr(t, "_last_level", "") != self.level or getattr(t, "_retry_partial", False):
                return t
        return None

    # ------------------------------------------------------------------ phase 3-5
    def _generate(self, t: Target, cards: list[str], fewshot: str | None, temperature: float,
                  extra: str = "") -> validate.Normalized | None:
        system, user = prompt.build_generation_prompt(t, self.s.mode, cards, fewshot, self.s.max_context_tokens,
                                                      extra_instruction=extra)
        raw = self.llm.generate(system, user, temperature, purpose="gen")
        norm = validate.normalize(raw, t, self.s.mode)
        for fx in norm.fixes:
            self.healing["l0:" + fx.split(":")[0]] += 1
        if not norm.ok:
            self.healing["l0_fail:" + norm.reason] += 1
            self.log.info("    L0 could not recover output (%s)", norm.reason)
            return None
        return norm

    def _gate(self, norm: validate.Normalized, t: Target, cards, fewshot, temperature) -> str | None:
        ok, reason, assertless = validate.static_gate(norm.src)
        if reason == "no_assert":
            # D12: the most common failure kind -> one regeneration with an explicit instruction
            self.healing["gate:no_assert_regen"] += 1
            norm2 = self._generate(t, cards, fewshot, temperature,
                                   extra="IMPORTANT: every test function MUST contain an assert statement "
                                         "comparing the function's result (the previous attempt had none).")
            if norm2 is None:
                return None
            ok, reason, assertless = validate.static_gate(norm2.src)
            norm.src = norm2.src
        if not ok:
            self.healing["gate_fail:" + reason.split(":")[0]] += 1
            self.log.info("    static gate rejected: %s", reason)
            return None
        if assertless:
            norm.src = validate.strip_functions(norm.src, set(assertless))
            self.healing["gate:assertless_stripped"] += len(assertless)
        return norm.src

    def _run_isolated(self, cand_path: Path, cand_bin: Path, with_cov: bool = True) -> tuple[cio.PytestResult, Path]:
        before = cio.backup_accum(self.ws)
        cand_json = cand_bin.with_suffix(".json")
        cand_bin.unlink(missing_ok=True)
        args = [str(cand_path)] + (cio.cov_args(self.ws, cand_json) if with_cov else [])
        r = cio.run_pytest(self.ws, args, self.s.pytest_timeout_s, cand_bin if with_cov else self.ws.cand_dir / "scratch.bin",
                           wall_timeout=self.s.pytest_timeout_s * 8 + 60)
        if cio.restore_accum_if_changed(self.ws, before):
            self.log.warning("    accumulated coverage file was touched by a candidate run; restored from backup")
            self.healing["accum_restored"] += 1
        if self._check_integrity(f"candidate run {cand_path.name}"):
            r.returncode = 99
            r.stderr = "integrity"
        return r, cand_json

    def _evaluate(self, t: Target, src: str, k: int) -> Eval:
        ws = self.ws
        stem = f"test_gen_{_safe(t.module)}_{_safe(t.qualname)}__c{k}"
        cand_path = ws.tests_dir / f"{stem}.py"
        cand_bin = ws.cand_dir / f"{stem}.bin"
        cand_path.write_text(src, encoding="utf-8")
        ev = Eval(passed=False, src=src, cand_path=cand_path, cand_bin=cand_bin)
        prunes = 0
        repairs = 0
        while True:
            if self.s.mode == "characterize":
                char = charmod.characterize(cand_path, ws.python, ws.repo_root, ws.child_env(),
                                            pytest_timeout=self.s.pytest_timeout_s)
                if self._check_integrity(f"characterize {cand_path.name}"):
                    ev.reason = "integrity"
                    return ev
                ev.char = char
                if char.dropped:
                    self.healing["char:dropped_tests"] += len(char.dropped)
                    self.log.info("    characterize: dropped %s (%s)", char.dropped, "; ".join(char.problems[:2]))
                if not char.ok:
                    cand_path.write_text(src, encoding="utf-8")   # keep original so pytest reports the real failure
                else:
                    src = char.src
                    ev.src = src
            r, cand_json = self._run_isolated(cand_path, cand_bin)
            if r.returncode == 99:
                ev.reason = "integrity"
                return ev
            if r.timed_out:
                ev.reason = "timeout"
                self.healing["l1:timeout_blacklist"] += 1
                return ev
            if r.returncode == 0:
                # flaky check: second run must also pass (no coverage needed)
                r2, _ = self._run_isolated(cand_path, ws.cand_dir / f"{stem}_re.bin", with_cov=False)
                if r2.returncode != 0:
                    flaky = {f.test_name for f in cio.parse_failures(r2.stdout) if f.test_name}
                    self.healing["l1:flaky_pruned"] += len(flaky)
                    self.log.info("    flaky tests pruned: %s", sorted(flaky))
                    remaining = set(validate.test_names(src)) - flaky
                    if not remaining or not flaky:
                        ev.reason = "flaky"
                        return ev
                    src = validate.strip_functions(src, flaky)
                    cand_path.write_text(src, encoding="utf-8")
                    ev.src = src
                    continue
                data = cio.coverage_json(ws, cand_bin, cand_json) if not cand_json.exists() else __import__("json").loads(cand_json.read_text(encoding="utf-8"))
                ev.executed = cio.executed_from_json(data)
                ev.gained = self.cov.contribution(ev.executed)
                ev.passed = True
                ev.n_llm_repairs, ev.n_prunes = repairs, prunes
                return ev
            failures = cio.parse_failures(r.stdout)
            ev.failures = failures
            kinds = Counter(f.kind for f in failures)
            self.log.info("    run failed (%s)", ", ".join(f"{k}x{v}" for k, v in kinds.items()) or f"rc={r.returncode}")
            if not failures:
                ev.reason = f"pytest rc={r.returncode}"
                self.log.debug(r.stdout[-1200:])
                return ev
            names = set(validate.test_names(src))
            failing = {f.test_name for f in failures if f.test_name}
            collection_error = any(f.test_name is None for f in failures)
            # L1 deterministic: prune failing tests when some tests pass
            if not collection_error and failing and failing < names and prunes < 2:
                src = validate.strip_functions(src, failing)
                cand_path.write_text(src, encoding="utf-8")
                ev.src = src
                prunes += 1
                for f in failures:
                    self.healing["l1:pruned:" + f.kind] += 1
                self.log.info("    L1 prune: removed %s, keeping %d tests", sorted(failing), len(names - failing))
                continue
            # L1 with LLM: compact failure -> full module rewrite
            if repairs < self.s.max_repair and self._budget_ok():
                card = "patching" if any(f.kind == "AttributeError" for f in failures) else None
                system, user = prompt.build_repair_prompt(t, src, failures, self.s.mode, card)
                try:
                    raw = self.llm.generate(system, user, self.s.temperature_repair, purpose="repair")
                except BudgetExceeded:
                    ev.reason = "budget"
                    return ev
                norm = validate.normalize(raw, t, self.s.mode)
                ok = norm.ok and validate.static_gate(norm.src)[0]
                repairs += 1
                self.healing["l1:llm_repair"] += 1
                if not ok:
                    self.healing["l1:llm_repair_unusable"] += 1
                    ev.reason = "repair_unusable"
                    return ev
                src = norm.src
                cand_path.write_text(src, encoding="utf-8")
                ev.src = src
                continue
            ev.reason = "failed:" + ",".join(sorted(kinds))
            return ev

    def process_target(self, t: Target) -> bool:
        ws = self.ws
        t.attempts += 1
        t._last_level = self.level
        t._retry_partial = False
        cards = t.select_cards(self.s.mode, self.type_cards)
        fewshot = prompt.find_fewshot(ws.tests_dir)
        self.log.info("TARGET %s  missing=%d %s  level=%s cards=%s attempt=%d", t.key, len(t.missing),
                      "(never executed)" if t.fully_uncovered else "(line-group " + ",".join(f"{a}-{b}" for a, b in t.missing_groups[:6]) + ")",
                      self.level, cards, t.attempts)
        self.events.emit("target_start", target=t.key, missing=len(t.missing), full=t.fully_uncovered,
                         level=self.level, cards=cards, attempt=t.attempts)
        best: Eval | None = None
        evals: list[Eval] = []
        reasons: list[str] = []
        try:
            for k in range(self.n_candidates):
                if not self._budget_ok():
                    break
                temp = self.s.temperature if k == 0 else self.s.temperature_retry
                norm = self._generate(t, cards, fewshot, temp)
                if norm is None:
                    reasons.append("l0")
                    continue
                src = self._gate(norm, t, cards, fewshot, temp)
                if src is None:
                    reasons.append("gate")
                    continue
                ev = self._evaluate(t, src, k)
                evals.append(ev)
                self.events.emit("candidate", target=t.key, k=k, passed=ev.passed, gained=ev.gained,
                                 reason=ev.reason, repairs=ev.n_llm_repairs, prunes=ev.n_prunes,
                                 tests=len(validate.test_names(ev.src)))
                if ev.passed:
                    self.log.info("    candidate %d PASSED, new lines covered: %d/%d", k, ev.gained, len(t.missing))
                    if best is None or ev.gained > best.gained:
                        best = ev
                    if best.gained >= len(t.missing):
                        break
                else:
                    reasons.append(ev.reason)
                    if ev.reason in ("timeout", "integrity"):
                        t.blacklisted = True
                        self.healing["blacklist:" + ev.reason] += 1
                        break
        finally:
            # cleanup: remove every candidate file except the winner (renamed below)
            for ev in evals:
                if ev is not best and ev.cand_path:
                    ev.cand_path.unlink(missing_ok=True)
                if ev.cand_bin:
                    for p in ws.cand_dir.glob(ev.cand_bin.stem + "*"):
                        if ev is not best or p.suffix != ".bin":
                            p.unlink(missing_ok=True)
        if best is None or best.gained == 0:
            reason = "no_gain(duplicate)" if best is not None else ",".join(sorted(set(reasons))) or "none"
            if best is not None and best.cand_path:
                best.cand_path.unlink(missing_ok=True)
                best.cand_bin.unlink(missing_ok=True)
            t.fail_reasons.append(reason)
            self.rejected.append({"target": t.key, "reason": reason, "level": self.level})
            self.log.info("  REJECTED %s (%s)", t.key, reason)
            self.events.emit("target_rejected", target=t.key, reason=reason)
            return False
        self._accept(t, best)
        return True

    def _accept(self, t: Target, ev: Eval) -> None:
        ws = self.ws
        final = ws.tests_dir / f"test_gen_{_safe(t.module)}_{_safe(t.qualname)}.py"
        n = 2
        while final.exists():
            final = ws.tests_dir / f"test_gen_{_safe(t.module)}_{_safe(t.qualname)}_{n}.py"
            n += 1
        shutil.move(str(ev.cand_path), str(final))
        cio.merge_into_accum(ws, ev.cand_bin)
        ev.cand_bin.unlink(missing_ok=True)
        gained = self.cov.apply(ev.executed)
        n_tests, n_asserts = validate.count_asserts(ev.src)
        n_char = sum(1 for name in validate.test_names(ev.src) if name.startswith("test_characterize_"))
        if ev.char is not None and ev.char.filled and n_char == 0:
            n_char = n_tests
        rec = Accepted(target=t.key, file=final.relative_to(ws.repo_root).as_posix(), tests=n_tests,
                       asserts=n_asserts, characterized=n_char, gained=gained, percent_after=self.cov.percent,
                       suspicious=(ev.char.suspicious if ev.char else []), level=self.level,
                       llm_repairs=ev.n_llm_repairs, prunes=ev.n_prunes)
        self.accepted.append(rec)
        t.accepted_files.append(rec.file)
        remaining = [ln for ln in t.missing if ln in self.cov.missing.get(t.file, set())]
        if len(remaining) >= 2 and t.attempts < self.s.max_attempts_per_target:
            t._retry_partial = True
        self.log.info("  ACCEPTED %s -> %s  (+%d lines, %d tests, %d asserts, %d characterized)  coverage now %.2f%%",
                      t.key, rec.file, gained, n_tests, n_asserts, n_char, self.cov.percent)
        self.events.emit("target_accepted", target=t.key, file=rec.file, gained=gained, tests=n_tests,
                         percent=round(self.cov.percent, 2), suspicious=rec.suspicious)

    # ------------------------------------------------------------------ L3 ladder
    def _escalate(self) -> None:
        if self.level == "S0":
            self.level = "S1"
            self.n_candidates = max(6, self.s.candidates * 2)
            self.type_cards = 2
            self.log.warning("L3 escalation -> S1: candidates=%d, rule cards=2, temperature=%.1f for extra candidates",
                             self.n_candidates, self.s.temperature_retry)
        self.max_level = self.level
        self.events.emit("escalation", level=self.level)

    def _recheck(self) -> None:
        data = cio.coverage_json(self.ws, self.ws.accum, self.ws.cov_dir / "recheck.json")
        fresh = CovState.from_json(data)
        drift = fresh.percent - self.cov.percent
        if abs(drift) > 0.01:
            self.log.info("recheck: accounting drift %.2f%%p corrected (accum says %.2f%%)", drift, fresh.percent)
        self.cov = fresh
        self.targets = tmod.refresh(self.targets, self.cov)

    # ------------------------------------------------------------------ main loop
    def run_loop(self) -> None:
        stall = 0
        since_recheck = 0
        s3_logged = False
        while True:
            if self.cov.percent >= self.s.target_coverage:
                self.stop_reason = "target reached (accounting)"
                break
            if not self._budget_ok():
                break
            t = self._next_target()
            if t is None:
                self.stop_reason = "target queue exhausted"
                break
            if not t.is_pure and not s3_logged:
                self.log.warning("L3 -> S3: pure-function queue exhausted, opening I/O-dependent targets")
                self.max_level = "S3" if self.max_level in ("S0", "S1") else self.max_level
                self.events.emit("escalation", level="S3")
                s3_logged = True
            try:
                ok = self.process_target(t)
            except BudgetExceeded as e:
                self.stop_reason = str(e)
                break
            except IntegrityViolation:
                t.blacklisted = True
                if self.s.fail_on_integrity:
                    self.stop_reason = "integrity violation (FAIL_ON_INTEGRITY_VIOLATION=true)"
                    break
                continue
            if ok:
                stall = 0
                since_recheck += 1
                self.targets = tmod.refresh(self.targets, self.cov)
                if since_recheck >= self.s.full_recheck_every:
                    self._recheck()
                    since_recheck = 0
            else:
                stall += 1
                if stall >= self.s.stall_s1 and self.level == "S0":
                    self._escalate()
                if stall >= self.s.stall_threshold:
                    self.stop_reason = f"stalled: {stall} consecutive targets without acceptance"
                    break
        self.log.info("loop finished: %s  (accounting coverage %.2f%%, accepted %d, rejected %d, llm calls %d)",
                      self.stop_reason, self.cov.percent, len(self.accepted), len(self.rejected), self.llm.calls)

    # ------------------------------------------------------------------ L5 + gate
    def finalize(self) -> None:
        ws = self.ws
        final_bin = ws.cov_dir / "final.bin"
        final_json = ws.cov_dir / "final.json"
        for round_no in range(1, 5):
            final_bin.unlink(missing_ok=True)
            r = cio.run_pytest(ws, ["tests"] + self._deselect_args() + cio.cov_args(ws, final_json),
                               self.s.pytest_timeout_s, final_bin, wall_timeout=3600)
            self._check_integrity("full suite")
            failures = cio.parse_failures(r.stdout)
            gen_failures = [f for f in failures if "test_gen_" in f.nodeid]
            if r.returncode in (0, 5) or not gen_failures:
                if failures:
                    self.suite_notes.append(f"{len(failures)} failures remain in non-generated tests")
                break
            # L5: interference / order dependence -> remove the failing generated tests
            self.log.warning("L5 suite healing round %d: %d generated tests fail in the full run", round_no, len(gen_failures))
            by_file: dict[str, set[str]] = {}
            for f in gen_failures:
                by_file.setdefault(f.nodeid.split("::")[0], set()).add(f.test_name or "*")
            for rel, names in by_file.items():
                p = ws.repo_root / rel
                if not p.exists():
                    continue
                if "*" in names:
                    p.unlink()
                    self.suite_notes.append(f"removed {rel} (collection error in full run)")
                    continue
                src = validate.strip_functions(p.read_text(encoding="utf-8"), names)
                if validate.test_names(src):
                    p.write_text(src, encoding="utf-8")
                    self.suite_notes.append(f"removed {sorted(names)} from {rel} (L5)")
                else:
                    p.unlink()
                    self.suite_notes.append(f"removed {rel} entirely (L5)")
                self.healing["l5:removed"] += len(names)
        if final_json.exists():
            data = __import__("json").loads(final_json.read_text(encoding="utf-8"))
            self.cov = CovState.from_json(data)
            self.final_percent = self.cov.percent
        else:
            self.final_percent = self.cov.percent
        # hard gate: only the exit code of --cov-fail-under decides
        gate = cio.run_pytest(ws, ["tests"] + self._deselect_args() + cio.cov_args(ws, None)
                              + [f"--cov-fail-under={self.s.target_coverage}"],
                              self.s.pytest_timeout_s, ws.cov_dir / "gate.bin", wall_timeout=3600)
        self._check_integrity("gate run")
        self.gate_passed = gate.returncode == 0
        m = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+(?:\.\d+)?)%", gate.stdout)
        if m:
            self.final_percent = float(m.group(1))
        self.log.info("GATE %s: coverage %.2f%% (target %.0f%%), pytest exit code %d",
                      "PASSED" if self.gate_passed else "FAILED", self.final_percent, self.s.target_coverage, gate.returncode)
        self.events.emit("gate", passed=self.gate_passed, percent=self.final_percent, exit_code=gate.returncode)

    # ------------------------------------------------------------------ attribution
    def attribution(self) -> dict[str, int]:
        """Remaining gaps by bucket (line counts). Reported when the gate is not met."""
        buckets: Counter = Counter()
        remaining_targets = tmod.refresh(list(self.targets), self.cov) if self.targets else []
        claimed: dict[str, set[int]] = {}
        for t in remaining_targets:
            claimed.setdefault(t.file, set()).update(t.missing)
            n = len(t.missing)
            if t.is_async:
                buckets["framework/async"] += n
            elif any("timeout" in r for r in t.fail_reasons) or (t.end - t.lineno) > 60:
                buckets["refactor_needed"] += n
            elif t.io_deps:
                buckets["io_dependent"] += n
            else:
                buckets["pure_logic"] += n
        for f, miss in self.cov.missing.items():
            rest = miss - claimed.get(f, set())
            buckets["module_level/dead"] += len(rest)
        return dict(buckets)
