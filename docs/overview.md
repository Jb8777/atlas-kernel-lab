# Overview

## Purpose

atlas-kernel-lab is a development and experimentation fork of atlas-kernel-clean. It extends the base routing and execution engine with a script-driven bring-up workflow, a VS Code developer harness, structured logging, a richer API request model, and a multi-backend LLM client with cascading fallback.

The project is local-first: Ollama is the default backend. Cloud backends (OpenRouter, Gemini CLI) are optional and configured via environment variables. An offline stub ensures the engine never hard-crashes when all backends are unavailable.

## Role in the Wider Stack

atlas-kernel-lab sits between a raw prompt and one or more backend tools or LLMs. It classifies incoming text into a route (code, research, ops, general), builds an execution plan, and then dispatches that plan to the appropriate backend. It is intended as the active development target where routing, execution, and LLM integration behaviour are iterated before being promoted to atlas-kernel-clean.

## How It Relates to atlas-kernel-clean

atlas-kernel-lab is forked from atlas-kernel-clean and extends it in the following confirmed ways:

- Script-driven bring-up: bootstrap.sh, run-api.sh, smoke.sh, smoke_test.sh, dev-env.sh
- VS Code developer harness: .vscode/launch.json, tasks.json, settings.json
- Structured logging: core/logger.py with rotating file handler
- Richer API request model: supports both legacy flat text and structured task/code/error/goal fields
- Expanded LLM backend: local (Ollama), Gemini CLI, OpenRouter, offline fallback, with cascade logic
- LLM routing: core/llm_router.py selects backend by task type keyword or LLM_BACKEND override
- Route-specific model selection in executor: MODEL_BY_ACTION table sets OLLAMA_MODEL per action
- Agents stub: agents/ directory present as empty scaffold for future expansion

## Key Files and Modules

| Path | Role |
|------|------|
| main.py | FastAPI application factory with lifespan logging setup |
| cli.py | CLI entrypoint: route_text to execute_route to run_execution |
| api/routes.py | /v1/health and /v1/route endpoints; builds effective input from structured or flat payload |
| core/router.py | Heuristic keyword router; classifies input into code, research, ops, general; config-augmentable |
| core/executor.py | Builds ExecutionPlan; runs multi-step, if/else, loop, and single-step execution |
| core/llm_client.py | Backend implementations: local (Ollama), Gemini CLI, OpenRouter, fallback stub; cascade logic |
| core/llm_router.py | Routes task type to backend: local, gemini, openrouter, fallback; LLM_BACKEND override |
| core/config_loader.py | Loads .env and Settings; loads config/model_router.json via load_json_config() |
| core/logger.py | Sets up console + rotating file logging; idempotent across API, CLI, and tests |
| tools/shell.py | Allowlisted shell execution: ls, pwd, whoami, date, uname only |
| tools/http.py | HTTP GET with certifi TLS; truncates response at 2000 chars |
| config/model_router.json | Routing keyword extensions and a models section (routing section consumed; models section not consumed) |
| .env.example | Baseline environment variable template |
| scripts/bootstrap.sh | One-shot venv + pip install + .env copy |
| scripts/run-api.sh | Activates venv, sources dev-env.sh, starts uvicorn on port 8010 |
| scripts/dev-env.sh | Exports LLM_BACKEND, OLLAMA_MODEL, OLLAMA_HOST, PYTHONUNBUFFERED, LLM_TIMEOUT_S |
| scripts/smoke.sh | Runs pytest, CLI code route, CLI general route, API import check |
| scripts/smoke_test.sh | POSTs scripts/smoke_payload.json to /v1/route via curl |
| scripts/smoke_payload.json | Structured code debug payload for smoke test |
| agents/ | Stub directory; agents.server:app referenced in launch.json but not yet implemented |
| .vscode/ | VS Code launch configs, tasks (smoke test, pytest, Ollama tags), and editor settings |
| tests/ | pytest suite: test_executor.py, test_router.py |

## Entrypoints

- **API (script):** `bash scripts/run-api.sh` — activates venv, sets dev env vars, starts uvicorn on port 8010
- **API (direct):** `uvicorn main:app --reload --host 127.0.0.1 --port 8010`
- **CLI:** `python cli.py "<input text>"`
- **Tests:** `pytest -q`

> **Note:** The README documents port 8000, but scripts/run-api.sh and all .vscode configs use port 8010. Port 8010 is the confirmed development port.
