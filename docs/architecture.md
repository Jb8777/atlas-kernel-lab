# Architecture

## Overview

atlas-kernel-lab is a FastAPI application with a CLI entrypoint, a heuristic keyword router, a multi-step execution engine, and a multi-backend LLM client. It extends atlas-kernel-clean with structured logging, a richer API request model, LLM backend routing, and a script-driven developer workflow.

## Module Reference

### main.py

FastAPI application factory. Creates the `app` instance via `create_app()`, registers `/v1` routes from `api/routes.py`, and sets up a lifespan context manager that calls `setup_logging()` on startup using settings from `config_loader.get_settings()`.

### cli.py

CLI entrypoint. Accepts one positional argument (input text). Calls `route_text()` → `execute_route()` → `run_execution()` and prints the result as formatted JSON containing `routing`, `execution`, and `result` fields.

### api/routes.py

Defines two routes under the `/v1` prefix:

- `GET /v1/health` — returns `{status, service, env}` from Settings. Safe to call without any LLM backend running.
- `POST /v1/route` — accepts `RouteRequest`, builds an effective input string via `build_effective_input()`, runs the full route-plan-execute pipeline, and returns `RouteResponse` with routing, execution, and result.

`RouteRequest` supports two payload shapes:
- **Legacy flat:** `{"text": "..."}`
- **Structured:** `{"task": "...", "code": "...", "error": "...", "goal": "..."}`

`build_effective_input()` uses `text` if present; otherwise concatenates task/code/error/goal into a single prompt string. Raises HTTP 400 if neither is provided.

### core/router.py

Heuristic keyword router. Classifies input into one of four routes: `code`, `research`, `ops`, `general`.

Detection order:
1. URL fast-path: `http`/`www` in text → ops
2. Command fast-path: `run`/`execute`/`ls` in text → ops
3. Code keywords (bug, debug, python, fastapi, etc.) → code
4. Research keywords (research, summarize, compare, etc.) → research
5. Ops keywords (deploy, kubernetes, docker, etc.) → ops
6. Default → general

The `routing` section of `config/model_router.json` can extend keyword lists (code_keywords, research_keywords, ops_keywords). This is consumed at runtime. The `models` section in the same file is not consumed.

### core/executor.py

Builds `ExecutionPlan` (route, action, next_steps) without I/O — safe to call in tests.

`run_execution()` is the full agent execution engine. It supports:

- **Task auto-planning:** if input contains "analyze", "audit", "investigate", or "review" and no "then" steps, calls `_expand_to_steps()` (LLM) to decompose the task.
- **Multi-step ("then"):** splits input on "then"; each step is classified and executed independently.
- **Conditional branching:** steps starting with "if" evaluate a condition via the LLM; steps starting with "else" toggle skip mode.
- **Loops:** steps matching `repeat N times <cmd>` execute the inner command N times (capped at 10).
- **Single-step (legacy):** if no "then" is present and no planning triggered, dispatches directly to run_shell, http_fetch, or LLM.

`MODEL_BY_ACTION` in executor.py maps action types to Ollama model names and temporarily sets `OLLAMA_MODEL` via env var during the call:

| Action | Model |
|--------|-------|
| llm_code | deepseek-coder:6.7b |
| llm_ops | deepseek-coder:6.7b |
| llm_research | mistral |
| llm_general | mistral |

These models are set by executor, not by config/model_router.json.

### core/llm_client.py

Provides `call_llm()` as the single public LLM interface. Backend selection order:

1. `LLM_BACKEND` env var (hard override: local, gemini, openrouter, fallback)
2. Task-type keyword routing via `core/llm_router.route_llm()`
3. `openrouter` as default cloud fallback

Cascade on failure:
1. Primary backend attempt
2. OpenRouter (if primary was not openrouter)
3. Offline stub (never raises — returns a static message)

Backend implementations:
- **local:** HTTP POST to `OLLAMA_HOST/api/generate` with `OLLAMA_MODEL`; default timeout `LLM_TIMEOUT_S` (120s)
- **gemini:** subprocess `gemini -p "<prompt>"`; raises `LLMClientError` if binary not on PATH
- **openrouter:** HTTP POST to `https://openrouter.ai/api/v1/chat/completions`; requires `OPENROUTER_API_KEY`
- **fallback:** Returns static string; logs warning

### core/llm_router.py

Routes task-type string to a backend name. Priority:

1. `LLM_BACKEND` env var override
2. Keyword table: code/debug/refactor/python/function/class → local; analyze/audit/investigate/review/compare → gemini
3. Default: openrouter

### core/config_loader.py

Loads environment variables (via `python-dotenv`) and returns a frozen `Settings` dataclass. Settings include: `app_env`, `app_name`, `log_level`, `config_path`, `logs_dir`. Cached for process lifetime via `@lru_cache`.

`load_json_config()` reads `config/model_router.json` with safe fallbacks: missing file, invalid JSON, and non-object root all return `{}`.

### core/logger.py

Sets up a root logger with a console `StreamHandler` and a `RotatingFileHandler` (5MB, 3 backups) writing to `logs/app.log`. Idempotent — safe to call from API lifespan, CLI startup, and tests.

### tools/shell.py

Allowlisted shell command executor. Only the following commands are permitted: `ls`, `pwd`, `whoami`, `date`, `uname`. Any other command prefix returns `"BLOCKED: Command not allowed"`. Timeout is 10 seconds.

### tools/http.py

HTTP GET via `requests` with `certifi` TLS verification. Response is truncated at 2000 characters. Returns error string on exception.

> **Dependency gap:** `certifi` is imported in `tools/http.py` but is not declared in `requirements.txt`. It may be installed as a transitive dependency of `requests`, but it is not explicitly pinned.

## Key Configuration: config/model_router.json

```json
{
  "routing": {
    "code_keywords": ["typescript", "javascript", "golang", "rust", "lint", "mypy", "type error"],
    "research_keywords": ["literature", "survey", "review", "findings", "hypothesis"],
    "ops_keywords": ["terraform", "helm", "ci/cd", "pipeline", "rollback", "slo", "sla"]
  },
  "models": {
    "code": "openai/gpt-4o",
    "research": "openai/gpt-4o",
    "ops": "openai/gpt-4o",
    "general": "openai/gpt-3.5-turbo"
  }
}
```

The `routing` section is consumed by `core/router.py` to extend keyword lists. The `models` section is present in config but is not consumed by any implementation — model selection is handled separately by `MODEL_BY_ACTION` in executor.py and by `OLLAMA_MODEL` / `OPENROUTER_MODEL` env vars.

## Request Lifecycle

```
HTTP POST /v1/route
  → build_effective_input()       (text or task/code/error/goal → single string)
  → route_text()                  (keyword heuristic → RouteResult with route, rationale)
  → execute_route()               (route → ExecutionPlan with action, next_steps) [no I/O]
  → run_execution()               (plan → dispatches to LLM/shell/http, multi-step if needed)
  → RouteResponse                 (routing + execution + result)
```

## Agents Stub

The `agents/` directory contains only `__init__.py`. The VS Code `launch.json` references `agents.server:app` as a second launch target, but `agents/server.py` does not exist. This config will fail until `agents/server.py` is implemented.

## VS Code Dev Harness

| File | Purpose |
|------|---------|
| .vscode/launch.json | Two debug launch configs for main:app and agents.server:app (port 8010) |
| .vscode/tasks.json | Smoke test, pytest, Ollama tags tasks |
| .vscode/settings.json | Python interpreter path (.venv), format on save, trailing whitespace trim |

## Safety Boundaries

- Shell tool: allowlist enforced in `tools/shell.py` (ls, pwd, whoami, date, uname only)
- Loop execution: capped at 10 iterations in `run_execution()`
- HTTP: response truncated at 2000 chars; TLS verification via certifi
- LLM: always cascades to offline fallback — never propagates an unhandled exception to the caller

## How atlas-kernel-lab Differs from atlas-kernel-clean

| Feature | atlas-kernel-clean | atlas-kernel-lab |
|---------|-------------------|-----------------|
| Helper scripts | None | bootstrap.sh, run-api.sh, dev-env.sh, smoke.sh, smoke_test.sh |
| VS Code harness | None | launch.json, tasks.json, settings.json |
| Logging | Not present | core/logger.py (rotating file + console) |
| API request model | text only | text or structured task/code/error/goal |
| LLM backend | local + openrouter + fallback | local + gemini + openrouter + fallback + cascade |
| LLM routing | Not present | core/llm_router.py (keyword + LLM_BACKEND override) |
| Route-specific models | Not present | MODEL_BY_ACTION in executor.py |
| Agents scaffold | Not present | agents/ stub directory |
| Dev port | 8000 | 8010 (scripts and VS Code) |
