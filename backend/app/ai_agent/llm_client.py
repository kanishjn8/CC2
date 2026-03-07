"""
LLM client — Gemini integration with automatic fallback chain:

  1. Gemini 3.1 Flash  (primary)
  2. Gemini 3.1 Flash Lite  (fallback)
  3. None  →  caller falls back to rule-based logic

Every function in the agent that uses this client already has a
rule-based fallback, so LLM failures are always graceful.
"""

import json
import traceback
from typing import Optional

import google.generativeai as genai

from app.config import GEMINI_API_KEY, GEMINI_PRIMARY_MODEL, GEMINI_FALLBACK_MODEL

_configured = False


def _ensure_configured():
    global _configured
    if not _configured and GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        _configured = True


def call_llm(
    prompt: str,
    system_instruction: str = "",
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> Optional[str]:
    """Call Gemini with primary → fallback → None chain.

    Returns the response text, or None if both models fail
    (so the caller can seamlessly fall back to rule-based logic).
    """
    if not GEMINI_API_KEY:
        return None

    _ensure_configured()

    for model_name in [GEMINI_PRIMARY_MODEL, GEMINI_FALLBACK_MODEL]:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction or None,
                generation_config=genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            response = model.generate_content(prompt)
            if response and response.text:
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
