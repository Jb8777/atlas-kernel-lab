# Setup

## Prerequisites

- Python 3.11 or later
- Git
- Ollama installed and running (required for the default local backend)
- Optional: `gemini` CLI on PATH (for Gemini backend)
- Optional: OpenRouter API key (for cloud fallback)

## Bootstrap Flow

Run the bootstrap script once after cloning. It creates the virtualenv, installs dependencies, and copies `.env.example` to `.env` if no `.env` file exists:

```bash
bash scripts/bootstrap.sh
```

What bootstrap.sh does:
1. Resolves the repo root from the script location (`cd "$(dirname "$0")/..")`)
2. Creates `.venv/` with `python3 -m venv .venv`
3. Activates the venv and upgrades pip
4. Installs `requirements.txt`
5. Copies `.env.example` to `.env` if `.env` does not already exist
6. Prints "Bootstrap complete."

## Environment Variables

Edit `.env` after bootstrapping. The following variables are confirmed in source:

| Variable | Source | Default | Description |
|----------|--------|---------|-------------|
| LLM_BACKEND | .env.example, dev-env.sh, llm_router.py | (none) | Force backend: local, gemini, openrouter, fallback |
| OLLAMA_MODEL | .env.example, dev-env.sh, llm_client.py | codellama | Ollama model name |
| OLLAMA_HOST | .env.example, dev-env.sh, llm_client.py | http://localhost:11434 | Ollama base URL |
| OPENROUTER_API_KEY | .env.example, llm_client.py | (empty) | Required for OpenRouter cloud backend |
| LLM_TIMEOUT_S | dev-env.sh, llm_client.py | 120 | LLM request timeout in seconds |
| APP_ENV | config_loader.py | development | Application environment label |
| APP_NAME | config_loader.py | AtlasKernel | Application name used in FastAPI metadata |
| LOG_LEVEL | config_loader.py | INFO | Logging level |
| CONFIG_PATH | config_loader.py | config/model_router.json | Path to JSON config |
| LOGS_DIR | config_loader.py | logs/ | Directory for rotating log files |
| PYTHONUNBUFFERED | dev-env.sh | 1 | Set by dev-env.sh for real-time log output |

> **Docs gap:** `LLM_TIMEOUT_S`, `APP_ENV`, `APP_NAME`, `LOG_LEVEL`, `CONFIG_PATH`, `LOGS_DIR`, and `PYTHONUNBUFFERED` are used in source but are absent from `.env.example`.

The `scripts/dev-env.sh` script exports a working local set of these variables. It is sourced automatically by `scripts/run-api.sh`.

## Starting the API

Use the script (recommended for development — sources dev-env.sh, activates venv, uses port 8010):

```bash
bash scripts/run-api.sh
```

Or start directly (ensure venv is active and env vars are set):

```bash
source .venv/bin/activate
uvicorn main:app --reload --host 127.0.0.1 --port 8010
```

> **Port note:** `scripts/run-api.sh` and all VS Code launch configs use port **8010**. The README documents port 8000. Use 8010 in development.

## Health Validation

```bash
curl http://127.0.0.1:8010/v1/health
```

Expected response:

```json
{"status":"ok","service":"AtlasKernel","env":"development"}
```

## VS Code Developer Harness

The `.vscode/` directory provides:

- **launch.json** — Two debug launch configs: `Atlas API (main:app)` and `Atlas API (agents.server:app)`. Both start uvicorn on port 8010 with LLM_BACKEND=local and OLLAMA_MODEL=deepseek-coder:6.7b injected as env vars.
- **tasks.json** — Three tasks: `Atlas: Smoke test` (runs smoke_test.sh), `Atlas: Test` (runs pytest -q), `Atlas: Ollama tags` (lists available Ollama models via curl).
- **settings.json** — Sets the default Python interpreter to `.venv/bin/python` and enables format on save.

> **Note:** The `Atlas API (agents.server:app)` launch config references `agents.server:app`, which does not exist yet. The `agents/` directory is an empty stub. This config will fail until `agents/server.py` is implemented.

## Running Tests

```bash
source .venv/bin/activate
pytest -q
```

Tests are in `tests/test_executor.py` and `tests/test_router.py`. `execute_route()` is safe to call in tests — it builds a plan without making any I/O calls.

## Smoke Tests

Run all smoke checks (pytest + CLI + API import):

```bash
bash scripts/smoke.sh
```

Run the structured API smoke test (requires the API to be running on port 8010):

```bash
bash scripts/smoke_test.sh
```

`smoke_test.sh` POSTs the contents of `scripts/smoke_payload.json` to `http://127.0.0.1:8010/v1/route`.
