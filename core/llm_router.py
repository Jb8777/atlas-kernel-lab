from __future__ import annotations

"""
llm_router — decides which LLM backend to use for a given task type.

Backends
--------
local     : Ollama (http://localhost:11434) — best for code tasks; no API key needed.
gemini    : Google Gemini CLI (`gemini` binary) — best for analysis/reasoning.
openrouter: Cloud fallback via OpenRouter — catches everything else.
fallback  : Offline static stub — used when all other backends are unavailable.

Environment overrides
---------------------
LLM_BACKEND=local|gemini|openrouter|fallback
    Force a specific backend regardless of task type.
OLLAMA_MODEL=<name>  (default: codellama)
OLLAMA_HOST=<url>    (default: http://localhost:11434)
"""

import os

# Task-type → backend routing table.
# Checked in order; first match wins.
_ROUTING_TABLE: list[tuple[list[str], str]] = [
    (["code", "debug", "refactor", "python", "function", "class"], "local"),
    (["analyze", "audit", "investigate", "review", "compare"], "gemini"),
]

_VALID_BACKENDS = {"local", "gemini", "openrouter", "fallback"}


def route_llm(task_type: str) -> str:
    """
    Return the backend name for a given task type string.

    Priority:
    1. LLM_BACKEND env var (hard override)
    2. Keyword match against _ROUTING_TABLE
    3. "openrouter" as default cloud fallback
    """
    forced = os.getenv("LLM_BACKEND", "").strip().lower()
    if forced in _VALID_BACKENDS:
        return forced

    lowered = task_type.lower()
    for keywords, backend in _ROUTING_TABLE:
        if any(k in lowered for k in keywords):
            return backend

    return "openrouter"
