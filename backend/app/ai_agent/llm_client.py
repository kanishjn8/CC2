"""
LLM client — Gemini integration with automatic fallback chain:

  1. GEMINI_PRIMARY_MODEL   (from .env)
  2. GEMINI_FALLBACK_MODEL  (from .env)
  3. None  →  caller falls back to rule-based logic

All values (model names, API key, cooldown) are read from app.config on
every call, so changing .env and restarting is enough to change behaviour
globally — no code edits needed.

Every function in the agent that uses this client already has a
rule-based fallback, so LLM failures are always graceful.
"""

import json
import logging
import time
import traceback
from typing import Optional

from google import genai
from google.genai import types

import app.config as _cfg   # imported as module so values are always re-read live

log = logging.getLogger("cc2.llm")

_client: genai.Client | None = None
_client_api_key: str = ""    # tracks which key the client was built with
_last_call_time: float = 0.0  # monotonic time of the last successful call
_total_calls: int = 0
_total_skipped: int = 0
_total_failures: int = 0


def _get_client() -> "genai.Client | None":
    """Return (and lazily create) a genai.Client, rebuilding if the API key changed."""
    global _client, _client_api_key
    api_key = _cfg.GEMINI_API_KEY
    if not api_key:
        return None
    if _client is None or api_key != _client_api_key:
        _client = genai.Client(api_key=api_key)
        _client_api_key = api_key
    return _client


def call_llm(
    prompt: str,
    system_instruction: str = "",
    temperature: float = 0.3,
    max_tokens: int = 1024,
    caller: str = "",
) -> Optional[str]:
    """Call Gemini with primary → fallback → None chain.

    All config (API key, model names, cooldown) is read live from app.config
    so .env changes take effect on the next restart without touching this file.
    Returns the response text, or None if both models fail / cooldown active.
    """
    global _last_call_time, _total_calls, _total_skipped, _total_failures

    caller_tag = f"[{caller}] " if caller else ""

    # Read live config values on every call
    api_key  = _cfg.GEMINI_API_KEY
    primary  = _cfg.GEMINI_PRIMARY_MODEL
    fallback = _cfg.GEMINI_FALLBACK_MODEL
    cooldown = _cfg.LLM_CALL_COOLDOWN

    if not api_key:
        log.warning("🤖 %sLLM SKIP — no GEMINI_API_KEY configured", caller_tag)
        _total_skipped += 1
        return None

    # Rate-limit guard — skip if called too soon, caller falls back to rule-based
    now = time.monotonic()
    elapsed = now - _last_call_time
    if elapsed < cooldown:
        remaining = cooldown - elapsed
        log.debug(
            "🤖 %sLLM COOLDOWN — skipping (%.0fs remaining)",
            caller_tag, remaining,
        )
        _total_skipped += 1
        return None

    client = _get_client()
    if client is None:
        log.warning("🤖 %sLLM SKIP — client initialization failed", caller_tag)
        _total_skipped += 1
        return None

    prompt_preview = prompt[:80].replace("\n", " ")
    log.info("🤖 %sLLM CALL — %s…", caller_tag, prompt_preview)

    for model_name in [primary, fallback]:
        if not model_name:
            continue
        try:
            t0 = time.monotonic()
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction or None,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            duration = time.monotonic() - t0
            if response and response.text:
                _last_call_time = time.monotonic()  # reset cooldown on success
                _total_calls += 1
                text = response.text.strip()
                log.info(
                    "🤖 %sLLM ✅ model=%s  %.1fs  %d chars",
                    caller_tag, model_name, duration, len(text),
                )
                log.debug("🤖 %sLLM RESPONSE: %s", caller_tag, text[:300])
                return text
        except Exception:
            _total_failures += 1
            log.error(
                "🤖 %sLLM ❌ FAILED — model=%s  [total failures: %d]\n%s",
                caller_tag, model_name, _total_failures, traceback.format_exc(),
            )
            continue

    _total_failures += 1
    log.error("🤖 %sLLM ❌ ALL MODELS FAILED — falling back to rule-based", caller_tag)
    return None  # Both models failed → caller uses rule-based


def call_llm_json(
    prompt: str,
    system_instruction: str = "",
    temperature: float = 0.2,
    max_tokens: int = 1024,
    caller: str = "",
) -> Optional[dict]:
    """Call LLM and parse the response as JSON. Returns None on any failure."""
    text = call_llm(prompt, system_instruction, temperature, max_tokens, caller=caller)
    if not text:
        return None

    # Strip markdown code fences if the model wraps output in ```json ... ```
    cleaned = text
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        parsed = json.loads(cleaned)
        log.debug("🤖 [%s] LLM JSON parsed OK: %s", caller, str(parsed)[:200])
        return parsed
    except json.JSONDecodeError:
        log.error("🤖 [%s] LLM JSON PARSE FAILED: %s", caller, text[:200])
        return None


def get_llm_stats() -> dict:
    """Return LLM usage statistics for monitoring."""
    return {
        "total_calls": _total_calls,
        "total_skipped": _total_skipped,
        "total_failures": _total_failures,
        "cooldown_seconds": _cfg.LLM_CALL_COOLDOWN,
        "api_key_set": bool(_cfg.GEMINI_API_KEY),
        "primary_model": _cfg.GEMINI_PRIMARY_MODEL,
        "fallback_model": _cfg.GEMINI_FALLBACK_MODEL,
    }
