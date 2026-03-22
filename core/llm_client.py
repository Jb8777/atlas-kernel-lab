from __future__ import annotations

import os
import subprocess
from typing import Any

import requests

from core.logger import get_logger

log = get_logger(__name__)

OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_TIMEOUT_S = int(os.getenv("LLM_TIMEOUT_S", "120"))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "codellama")


class LLMClientError(RuntimeError):
    """Raised when the LLM call cannot be completed safely."""


def _extract_text(payload: dict[str, Any]) -> str:
    """
    Extract assistant text from OpenRouter-compatible Chat Completions response.
    """
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LLMClientError("LLM response missing choices")

    first = choices[0]
    if not isinstance(first, dict):
        raise LLMClientError("LLM response choice is not a dict")

    message = first.get("message", {})
    content = message.get("content", "")
    if not isinstance(content, str):
        raise LLMClientError("LLM response content is not a string")

    return content


# ── Backend implementations ────────────────────────────────────────────────────

def _call_local(prompt: str) -> str:
    """
    Call a local Ollama instance (http://localhost:11434).

    Falls back with LLMClientError if Ollama is not running.
    """
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=DEFAULT_TIMEOUT_S,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("response", "")
        if not isinstance(text, str) or not text:
            raise LLMClientError("Empty response from local LLM")
        return text
    except requests.RequestException as e:
        raise LLMClientError(f"Local LLM unavailable: {e}") from e


def _call_gemini(prompt: str) -> str:
    """
    Call the Gemini CLI (`gemini` binary must be on PATH).

    Expects: gemini -p "<prompt>"
    """
    try:
        result = subprocess.run(
            ["gemini", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=DEFAULT_TIMEOUT_S,
        )
        output = (result.stdout or "").strip()
        if result.returncode != 0 or not output:
            err = (result.stderr or "").strip()
            raise LLMClientError(f"Gemini CLI error (rc={result.returncode}): {err}")
        return output
    except FileNotFoundError as e:
        raise LLMClientError("Gemini CLI not found on PATH") from e
    except subprocess.TimeoutExpired as e:
        raise LLMClientError("Gemini CLI timed out") from e


def _call_fallback(prompt: str) -> str:
    """
    Offline stub — returns a safe static response when all backends are down.
    """
    log.warning("All LLM backends unavailable; returning fallback stub.")
    return (
        "[FALLBACK] No LLM backend is available. "
        "Set OPENROUTER_API_KEY, start Ollama, or install the Gemini CLI."
    )


def _call_openrouter(prompt: str, *, model: str, system: str, temperature: float) -> str:
    """OpenRouter cloud backend (original implementation)."""
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise LLMClientError("OPENROUTER_API_KEY is not set")

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    body = {"model": model, "messages": messages, "temperature": temperature}
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/AtlasKernel",
        "X-Title": "AtlasKernel",
    }

    try:
        resp = requests.post(
            OPENROUTER_ENDPOINT,
            json=body,
            headers=headers,
            timeout=DEFAULT_TIMEOUT_S,
        )
        resp.raise_for_status()
        return _extract_text(resp.json())
    except requests.HTTPError as e:
        log.exception("LLM HTTP error: %s", e.response.text if e.response else "")
        raise LLMClientError(f"LLM HTTP error: {e}") from e
    except requests.RequestException as e:
        log.exception("LLM request failed")
        raise LLMClientError(f"LLM request failed: {e}") from e


# ── Public interface ───────────────────────────────────────────────────────────

def call_llm(
    prompt: str,
    *,
    model: str = "openai/gpt-3.5-turbo",
    system: str = "",
    temperature: float = 0.7,
    task_type: str = "",
) -> str:
    """
    Route prompt to the appropriate LLM backend and return the response text.

    Backend selection order:
    1. LLM_BACKEND env var (hard override)
    2. task_type keyword routing via llm_router.route_llm()
    3. openrouter as default cloud fallback

    On backend failure, cascades: primary → openrouter → fallback stub.
    """
    from core.llm_router import route_llm  # local import avoids circular deps

    backend = route_llm(task_type or prompt[:120])
    log.debug("llm backend selected: %s (task_type=%r)", backend, task_type)

    # Primary backend attempt
    try:
        if backend == "local":
            return _call_local(prompt)
        if backend == "gemini":
            return _call_gemini(prompt)
        if backend == "fallback":
            return _call_fallback(prompt)
        # "openrouter" or unknown
        return _call_openrouter(prompt, model=model, system=system, temperature=temperature)
    except LLMClientError as primary_err:
        log.warning("primary backend %r failed: %s — cascading", backend, primary_err)

    # Cascade 1: try openrouter if it wasn't already the primary
    if backend != "openrouter":
        try:
            return _call_openrouter(prompt, model=model, system=system, temperature=temperature)
        except LLMClientError as e:
            log.warning("openrouter cascade failed: %s", e)

    # Cascade 2: offline stub — never raises
    return _call_fallback(prompt)

