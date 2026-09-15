"""CLI: raise pytest coverage of a repository to the target (default 80%) with LLM-written tests.

    python main.py --repo <path-or-git-url> [--target 80] [--package core] [--mode characterize]

Exit code 0 only when `pytest --cov --cov-fail-under=<target>` passes on the full suite.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from core import env_setup, report
from core.config import AGENT_ROOT, load_settings
from core.llm import LLM
from core.logger import EventLog, setup_logger
from core.loop import IntegrityViolation, Pipeline


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="pytest coverage self-healing agent")
    ap.add_argument("--repo", help="local path or git URL of the target repository (default: REPO_URL in .env)")
    ap.add_argument("--target", type=float, help="target coverage percent (default: TARGET_COVERAGE in .env)")
    ap.add_argument("--package", help="source package(s) to measure, comma separated (default: auto-detect)")
    ap.add_argument("--mode", choices=["characterize", "strict"], help="generation mode")
    ap.add_argument("--candidates", type=int, help="best-of-N candidates per target")
    ap.add_argument("--max-calls", type=int, help="LLM call budget")
    ap.add_argument("--max-minutes", type=int, help="runtime budget in minutes")
    ap.add_argument("--venv", action="store_true", help="create a dedicated venv even for a local path")
    ap.add_argument("--dry-run", action="store_true", help="phase 0-2 only: baseline + target list, no LLM calls")
    ap.add_argument("--continue-on-integrity", action="store_true",
                    help="on a gate-3 violation: restore files, blacklist the target and continue (default: stop)")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = load_settings()
    repo = args.repo or settings.repo_url
    if not repo:
        print("error: --repo is required (or set REPO_URL in .env)", file=sys.stderr)
        return 2
    if args.target is not None:
        settings.target_coverage = args.target
    if args.package:
        settings.source_package = args.package
    if args.mode:
        settings.mode = args.mode
    if args.candidates:
        settings.candidates = args.candidates
    if args.max_calls:
        settings.max_llm_calls = args.max_calls
    if args.max_minutes:
        settings.max_runtime_minutes = args.max_minutes
    settings.use_venv = args.venv
    if args.continue_on_integrity:
        settings.fail_on_integrity = False
    settings.dry_run = args.dry_run

    run_id = time.strftime("%Y%m%d_%H%M%S")
    logs_dir = AGENT_ROOT / "logs"
    reports_dir = AGENT_ROOT / "reports"
    log_path = logs_dir / f"run_{run_id}.log"
    log = setup_logger(log_path)
    events = EventLog(reports_dir / f"events_{run_id}.jsonl")
    log.info("=== coverage agent run %s ===", run_id)
    log.info("repo=%s target=%.0f%% mode=%s candidates=%d model=%s", repo, settings.target_coverage,
             settings.mode, settings.candidates, settings.llm_model)

    ws = None
    pipeline = None
    exit_code = 1
    try:
        ws = env_setup.prepare(repo, settings, log)
        llm = LLM(settings, log, events)
        pipeline = Pipeline(ws, settings, log, events, llm, run_id)
        pipeline.baseline()
        pipeline.discover_targets()
        if settings.dry_run:
            log.info("dry run: %d targets listed, no LLM calls made", len(pipeline.targets))
            for t in pipeline.targets:
                log.info("  %-50s miss=%3d %s io=%s", t.key, len(t.missing), "FULL" if t.fully_uncovered else "part", t.io_deps)
            return 0
        if pipeline.cov.percent < settings.target_coverage:
            pipeline.run_loop()
        else:
            pipeline.stop_reason = "baseline already above target"
        pipeline.finalize()
        exit_code = 0 if pipeline.gate_passed else 1
    except IntegrityViolation as e:
        log.error("stopped: %s", e)
        exit_code = 3
    except KeyboardInterrupt:
        log.warning("interrupted by user; writing partial report")
        if pipeline is not None:
            pipeline.stop_reason = pipeline.stop_reason or "interrupted"
        exit_code = 130
    except Exception as e:  # noqa: BLE001 - report then exit non-zero
        log.exception("fatal: %s", e)
        exit_code = 4
    finally:
        if pipeline is not None and ws is not None and pipeline.cov is not None:
            try:
                md, mj = report.write_reports(pipeline, ws, settings, run_id, reports_dir, log_path)
                log.info("report: %s", md)
                log.info("metrics: %s", mj)
            except Exception as e:  # noqa: BLE001
                log.exception("report writing failed: %s", e)
        events.close()
    log.info("exit code %d", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
