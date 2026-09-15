"""Reports: run_<ts>.md (human), metrics.json (machine), healing_log.json (cross-run learning)."""
from __future__ import annotations

import json
import time
from pathlib import Path


def _pct(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.2f}%"


def build_markdown(p, ws, settings, run_id: str, log_path: Path) -> str:
    acc = p.accepted
    n_tests = sum(a.tests for a in acc)
    n_asserts = sum(a.asserts for a in acc)
    n_char = sum(a.characterized for a in acc)
    suspicious = [(a.file, s) for a in acc for s in a.suspicious]
    llm = p.llm.stats()
    attrib = p.attribution()
    lines = [
        f"# Coverage run {run_id} — `{ws.name}`",
        "",
        f"- 대상: `{ws.repo_root}`  (패키지: {', '.join(ws.packages)})",
        f"- 모델: `{llm['model']}` @ `{llm['base_url']}`  모드: **{settings.mode}**",
        f"- 실행 시간: {p._elapsed_min():.1f}분  LLM 호출: {llm['calls']}회 (prompt {llm['prompt_tokens']:,} / completion {llm['completion_tokens']:,} tokens)",
        f"- 로그: `{log_path}`",
        "",
        "## 결과",
        "",
        "| 항목 | 값 |",
        "|---|---|",
        f"| 베이스라인 커버리지 | {_pct(p.baseline_percent)} |",
        f"| 최종 커버리지 (전체 스위트 완주) | **{_pct(p.final_percent)}** |",
        f"| 목표 | {settings.target_coverage:.0f}% |",
        f"| 게이트 판정 (`--cov-fail-under` exit code) | **{'PASSED' if p.gate_passed else 'FAILED'}** |",
        f"| 종료 사유 | {p.stop_reason} |",
        f"| 수락 타깃 / 폐기 타깃 | {len(acc)} / {len(p.rejected)} |",
        f"| 생성 테스트 함수 / 단언 수 | {n_tests} / {n_asserts} (밀도 {n_asserts / n_tests:.2f}) |" if n_tests else "| 생성 테스트 함수 | 0 |",
        "",
        "## 정직성 세트",
        "",
        "| 항목 | 값 | 비고 |",
        "|---|---|---|",
        f"| characterize 테스트 비율 | {n_char}/{n_tests} ({(100 * n_char / n_tests) if n_tests else 0:.0f}%) | 현재 동작을 기록한 것이며 정답성은 검토 필요 |",
        f"| 분모 제외 | exclude_lines 기본셋(`__main__`, TYPE_CHECKING, abstractmethod, `...`) | 사람 승인 없이 omit 추가하지 않음 |",
        f"| 도달한 에스컬레이션 단계 | {p.max_level} | S0 기본 / S1 후보증폭 / S3 I/O 개방 |",
        f"| mutation score | 미측정 | 선택 항목 |",
        f"| 무결성 경보 | {len(p.integrity_alerts)} | 테스트 외 파일 변경 감지 횟수 |",
        "",
    ]
    if suspicious:
        lines += ["## 의심 목록 (캡처값이 None/빈 값/예외인 characterization 단언)", ""]
        for f, s in suspicious[:60]:
            lines.append(f"- `{f}` — {s}")
        lines.append("")
    lines += ["## 수락된 타깃", "", "| 타깃 | 파일 | 테스트 | +라인 | 누적 커버리지 | 단계 | 수리(LLM/prune) |", "|---|---|---|---|---|---|---|"]
    for a in acc:
        lines.append(f"| `{a.target}` | `{a.file}` | {a.tests} | +{a.gained} | {a.percent_after:.1f}% | {a.level} | {a.llm_repairs}/{a.prunes} |")
    lines.append("")
    if p.rejected:
        lines += ["## 폐기된 타깃", "", "| 타깃 | 사유 | 단계 |", "|---|---|---|"]
        for r in p.rejected:
            lines.append(f"| `{r['target']}` | {r['reason']} | {r['level']} |")
        lines.append("")
    lines += ["## 자가수리 카운터 (L0/L1/L5)", "", "| 조치 | 횟수 |", "|---|---|"]
    for k, v in sorted(p.healing.items()):
        lines.append(f"| {k} | {v} |")
    lines.append("")
    if p.suite_notes:
        lines += ["## L5 스위트 자가수리 / 비고", ""] + [f"- {n}" for n in p.suite_notes] + [""]
    if p.known_failures:
        lines += ["## 기존 실패 테스트 (수정하지 않고 deselect)", ""] + [f"- `{f.nodeid}` — {f.message[:120]}" for f in p.known_failures] + [""]
    if ws.excluded_modules or ws.env_notes:
        lines += ["## L2 환경 (부분 진행)", ""]
        for m, why in ws.excluded_modules.items():
            lines.append(f"- 제외 모듈 `{m}`: {why}")
        for n in ws.env_notes:
            lines.append(f"- {n}")
        lines.append("")
    lines += ["## 남은 공백 귀속 (라인 수)", "", "| 버킷 | 라인 |", "|---|---|"]
    for k, v in sorted(attrib.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {k} | {v} |")
    lines.append("")
    if not p.gate_passed:
        lines += ["> 게이트 미달. 위 귀속표의 `refactor_needed`/`io_dependent` 항목이 L4(리팩터 승인 게이트) 제안 대상입니다.",
                  "> 통과한 척하지 않습니다 (exit 1).", ""]
    if p.integrity_alerts:
        lines += ["## ⚠ 무결성 경보", ""] + [f"- {a}" for a in p.integrity_alerts] + [""]
    return "\n".join(lines)


def write_reports(p, ws, settings, run_id: str, reports_dir: Path, log_path: Path) -> tuple[Path, Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    md = reports_dir / f"run_{run_id}.md"
    md.write_text(build_markdown(p, ws, settings, run_id, log_path), encoding="utf-8")
    metrics = {
        "run_id": run_id, "repo": ws.name, "repo_root": str(ws.repo_root), "packages": ws.packages,
        "mode": settings.mode, "target": settings.target_coverage,
        "baseline_percent": round(p.baseline_percent, 2), "final_percent": p.final_percent,
        "gate_passed": p.gate_passed, "stop_reason": p.stop_reason, "max_level": p.max_level,
        "accepted": [a.__dict__ for a in p.accepted], "rejected": p.rejected,
        "healing": dict(p.healing), "llm": p.llm.stats(), "elapsed_min": round(p._elapsed_min(), 2),
        "known_failures": [f.nodeid for f in p.known_failures], "suite_notes": p.suite_notes,
        "integrity_alerts": p.integrity_alerts, "attribution": p.attribution(),
        "excluded_modules": ws.excluded_modules,
    }
    mpath = reports_dir / f"metrics_{run_id}.json"
    mpath.write_text(json.dumps(metrics, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (reports_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    update_healing_log(reports_dir / "healing_log.json", ws, p, settings)
    return md, mpath


def update_healing_log(path: Path, ws, p, settings) -> None:
    log = {}
    if path.exists():
        try:
            log = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log = {}
    gen_calls = max(1, p.llm.calls)
    l0 = sum(v for k, v in p.healing.items() if k.startswith("l0:"))
    entry = {
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "best_config": {"mode": settings.mode, "candidates": p.n_candidates, "level": p.max_level},
        "escalation_reached": p.max_level,
        "target_blacklist": [t.key for t in p.targets if t.blacklisted],
        "l0_fix_rate": round(l0 / gen_calls, 3),
        "l1_counts": {k: v for k, v in p.healing.items() if k.startswith("l1:")},
        "last_result": {"baseline": round(p.baseline_percent, 2), "final": p.final_percent, "gate": p.gate_passed},
        "runs": (log.get(ws.name, {}).get("runs", 0) + 1),
    }
    log[ws.name] = entry
    path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
