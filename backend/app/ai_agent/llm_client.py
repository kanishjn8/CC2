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
import time
import traceback
from typing import Optional

from google import genai
from google.genai import types

import app.config as _cfg   # imported as module so values are always re-read live

_client: genai.Client | None = None
_client_api_key: str = ""    # tracks which key the client was built with
_last_call_time: float = 0.0  # monotonic time of the last successful call


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
) -> Optional[str]:
    """Call Gemini with primary → fallback → None chain.

    All config (API key, model names, cooldown) is read live from app.config
    so .env changes take effect on the next restart without touching this file.
    Returns the response text, or None if both models fail / cooldown active.
    """
    global _last_call_time

    # Read live config values on every call
    api_key  = _cfg.GEMINI_API_KEY
    primary  = _cfg.GEMINI_PRIMARY_MODEL
    fallback = _cfg.GEMINI_FALLBACK_MODEL
    cooldown = _cfg.LLM_CALL_COOLDOWN

    if not api_key:
        return None

    # Rate-limit guard — skip if called too soon, caller falls back to rule-based
    now = time.monotonic()
    elapsed = now - _last_call_time
    if elapsed < cooldown:
        remaining = cooldown - elapsed
        print(
            f"[agent-llm] cooldown active — skipping LLM call "
            f"({remaining:.0f}s / {cooldown:.0f}s remaining)"
        )
        return None

    client = _get_client()
    if client is None:
        return None

    for model_name in [primary, fallback]:
        if not model_name:
            continue
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction or None,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            if response and response.text:
                _last_call_time = time.monotonic()  # reset cooldown on success
                print(f"[agent-llm] ✓ {model_name} responded")
                return response.text.strip()
        except Exception:
            print(f"[agent-llm] {model_name} failed:\n{traceback.format_exc()}")
            continue

    return None  # Both models failed → caller uses rule-based


def call_llm_json(
    prompt: str,
    system_instruction: str = "",
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> Optional[dict]:
    """Call LLM and parse the response as JSON. Returns None on any failure."""
    text = call_llm(prompt, system_instruction, temperature, max_tokens)
    if not text:
        return None

    # Strip markdown code fences if the model wraps output in ```json ... ```
    cleaned = text
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        print(f"[agent-llm] Failed to parse JSON from LLM response: {text[:200]}")
        return None
