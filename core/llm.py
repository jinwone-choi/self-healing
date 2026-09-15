"""OpenAI-compatible chat client used as a pure function: prompt in, text out.

No tools, no history, no state. One call == one target candidate. Budget-counted.
"""
from __future__ import annotations

import time

from .config import Settings, is_external_endpoint


class BudgetExceeded(RuntimeError):
    pass


class LLM:
    def __init__(self, settings: Settings, log, events=None):
        self.s = settings
        self.log = log
        self.events = events
        self.calls = 0
        self.failed_calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_latency = 0.0
        self._client = None
        if is_external_endpoint(settings.llm_base_url):
            log.warning("LLM endpoint %s is EXTERNAL: target source code will leave this machine "
                        "(set LLM_BASE_URL to the on-prem endpoint for internal repositories)",
                        settings.llm_base_url)

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(base_url=self.s.llm_base_url, api_key=self.s.llm_api_key or "dummy",
                                  timeout=self.s.timeout_s, max_retries=0)
        return self._client

    def generate(self, system: str, user: str, temperature: float, max_tokens: int | None = None,
                 purpose: str = "gen") -> str:
        if self.calls >= self.s.max_llm_calls:
            raise BudgetExceeded(f"LLM call budget exhausted ({self.s.max_llm_calls})")
        self.calls += 1
        last_err: Exception | None = None
        for attempt in range(3):
            t0 = time.time()
            try:
                resp = self.client.chat.completions.create(
                    model=self.s.llm_model,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    temperature=temperature,
                    max_tokens=max_tokens or self.s.max_tokens,
                )
                dt = time.time() - t0
                self.total_latency += dt
                text = (resp.choices[0].message.content or "") if resp.choices else ""
                usage = getattr(resp, "usage", None)
                pt = getattr(usage, "prompt_tokens", 0) or 0
                ct = getattr(usage, "completion_tokens", 0) or 0
                self.prompt_tokens += pt
                self.completion_tokens += ct
                self.log.debug("llm %s call#%d temp=%.1f %.1fs tokens=%d/%d", purpose, self.calls, temperature, dt, pt, ct)
                if self.events:
                    self.events.emit("llm_call", n=self.calls, purpose=purpose, temperature=temperature,
                                     latency=round(dt, 2), prompt_tokens=pt, completion_tokens=ct)
                return text
            except Exception as e:  # noqa: BLE001 - any transport/API error, retry with backoff
                last_err = e
                self.log.warning("llm call failed (attempt %d): %s", attempt + 1, str(e)[:200])
                time.sleep(1.5 * (attempt + 1))
        self.failed_calls += 1
        raise RuntimeError(f"LLM call failed after retries: {last_err}")

    def stats(self) -> dict:
        return {"calls": self.calls, "failed_calls": self.failed_calls,
                "prompt_tokens": self.prompt_tokens, "completion_tokens": self.completion_tokens,
                "avg_latency_s": round(self.total_latency / self.calls, 2) if self.calls else 0.0,
                "model": self.s.llm_model, "base_url": self.s.llm_base_url}
