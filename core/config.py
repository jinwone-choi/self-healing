"""Settings loaded from .env (OpenAI-compatible LLM + pipeline policy)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

AGENT_ROOT = Path(__file__).resolve().parent.parent


def _f(name: str, default: float) -> float:
    v = os.getenv(name, "").split("#")[0].strip()
    return float(v) if v else default


def _i(name: str, default: int) -> int:
    v = os.getenv(name, "").split("#")[0].strip()
    return int(v) if v else default


def _b(name: str, default: bool) -> bool:
    v = os.getenv(name, "").split("#")[0].strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


def _s(name: str, default: str = "") -> str:
    v = os.getenv(name, "").split("#")[0].strip()
    return v or default


@dataclass
class Settings:
    # LLM
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    temperature: float = 0.2
    temperature_retry: float = 0.8
    temperature_repair: float = 0.3
    max_tokens: int = 1536
    timeout_s: int = 120
    max_context_tokens: int = 4096
    # policy
    target_coverage: float = 80.0
    mode: str = "characterize"          # characterize | strict
    candidates: int = 3
    max_repair: int = 2
    stall_threshold: int = 20
    stall_s1: int = 10
    full_recheck_every: int = 10
    max_attempts_per_target: int = 3
    # budget
    max_llm_calls: int = 500
    max_runtime_minutes: int = 120
    # sandbox
    pytest_timeout_s: int = 30
    block_network: bool = True
    fail_on_integrity: bool = True
    # repo
    repo_url: str = ""
    repo_branch: str = ""
    source_package: str = ""
    python_bin: str = "python"
    use_venv: bool = False
    dry_run: bool = False
    extra: dict = field(default_factory=dict)


def load_settings(env_path: Path | None = None) -> Settings:
    load_dotenv(env_path or AGENT_ROOT / ".env", override=False)
    s = Settings()
    s.llm_base_url = _s("LLM_BASE_URL", "https://api.openai.com/v1")
    s.llm_api_key = _s("LLM_API_KEY") or _s("OPENAI_API_KEY")
    s.llm_model = _s("LLM_MODEL", "gpt-4o-mini")
    s.temperature = _f("LLM_TEMPERATURE", 0.2)
    s.temperature_retry = _f("LLM_TEMPERATURE_RETRY", 0.8)
    s.temperature_repair = _f("LLM_TEMPERATURE_REPAIR", 0.3)
    s.max_tokens = _i("LLM_MAX_TOKENS", 1536)
    s.timeout_s = _i("LLM_TIMEOUT_S", 120)
    s.max_context_tokens = _i("LLM_MAX_CONTEXT_TOKENS", 4096)
    s.target_coverage = _f("TARGET_COVERAGE", 80.0)
    s.mode = _s("GENERATION_MODE", "characterize")
    s.candidates = _i("CANDIDATES_PER_TARGET", 3)
    s.max_repair = _i("MAX_REPAIR_ATTEMPTS", 2)
    s.stall_threshold = _i("STALL_THRESHOLD", 20)
    s.stall_s1 = _i("STALL_S1", 10)
    s.full_recheck_every = _i("FULL_RECHECK_EVERY", 10)
    s.max_llm_calls = _i("MAX_LLM_CALLS", 500)
    s.max_runtime_minutes = _i("MAX_RUNTIME_MINUTES", 120)
    s.pytest_timeout_s = _i("PYTEST_TIMEOUT_S", 30)
    s.block_network = _b("BLOCK_NETWORK", True)
    s.fail_on_integrity = _b("FAIL_ON_INTEGRITY_VIOLATION", True)
    s.repo_url = _s("REPO_URL")
    s.repo_branch = _s("REPO_BRANCH")
    s.source_package = _s("SOURCE_PACKAGE")
    s.python_bin = _s("PYTHON_BIN", "python")
    return s


def is_external_endpoint(base_url: str) -> bool:
    """True when source code would leave the local network (security note in docs)."""
    u = base_url.lower()
    for marker in ("localhost", "127.0.0.1", "0.0.0.0", "://10.", "://192.168.", "://172.", ".local", ".internal", ".corp"):
        if marker in u:
            return False
    return True
