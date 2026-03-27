# Troubleshooting

## Bootstrap Failures

**Problem:** `bash scripts/bootstrap.sh` fails at `python3 -m venv .venv`

**Fix:** Ensure Python 3.11 or later is installed and `python3` is on PATH. On some systems you may need to install `python3-venv` separately:

```bash
sudo apt install python3-venv   # Debian/Ubuntu
```

**Problem:** `pip install -r requirements.txt` fails

**Fix:** Check the error output. Common causes are a missing system dependency (e.g. `libpq`) or a stale pip cache. Try:

```bash
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Problem:** `.env.example` was not copied to `.env`

**Fix:** Either re-run bootstrap.sh (it copies only if `.env` does not exist), or copy manually:

```bash
cp .env.example .env
```

## API Will Not Start

**Problem:** `bash scripts/run-api.sh` fails with "source: .venv/bin/activate: No such file or directory"

**Fix:** Bootstrap has not been run. Run `bash scripts/bootstrap.sh` first.

**Problem:** Port already in use

**Fix:** Kill the process using port 8010, or change the port in `scripts/run-api.sh`.

**Problem:** ImportError on startup

**Fix:** Activate the venv and verify all dependencies are installed:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## API Port Confusion

**Problem:** `curl http://127.0.0.1:8000/v1/health` returns "Connection refused"

**Fix:** The development port is 8010, not 8000. The README documents 8000 but scripts/run-api.sh and all VS Code configs use 8010. Use:

```bash
curl http://127.0.0.1:8010/v1/health
```

This is a known documentation gap — the README has not been updated to reflect the actual script port.

## Missing or Invalid Environment Variables

**Problem:** All LLM routes return the fallback stub message

**Check:** Ensure at least one backend is configured. Inspect current vars:

```bash
echo $LLM_BACKEND
echo $OLLAMA_HOST
echo $OPENROUTER_API_KEY
```

**Fix:** Source the dev environment:

```bash
source scripts/dev-env.sh
```

Or set variables in `.env`.

**Problem:** Variables set in `.env` are not being picked up

**Fix:** `python-dotenv` loads `.env` automatically via `config_loader.get_settings()`. If running with a script, make sure the script does not override the env vars before Python starts.

**Docs gap:** `LLM_TIMEOUT_S`, `APP_ENV`, `APP_NAME`, `LOG_LEVEL`, `CONFIG_PATH`, `LOGS_DIR`, and `PYTHONUNBUFFERED` are all consumed by the application but are absent from `.env.example`. See docs/setup.md for the full variable reference.

## Ollama Not Running

**Problem:** LLM responses show "Local LLM unavailable: ..."

**Fix:** Start Ollama:

```bash
ollama serve
```

Verify it is running:

```bash
curl http://127.0.0.1:11434/api/tags
```

**Problem:** Ollama is running but the requested model is not available

**Fix:** Pull the required models:

```bash
ollama pull deepseek-coder:6.7b
ollama pull mistral
```

**Problem:** `OLLAMA_HOST` points to a remote host that is not reachable

**Fix:** Verify the host and port. dev-env.sh and .env.example both default to `http://127.0.0.1:11434`. Update `OLLAMA_HOST` in `.env` or in `scripts/dev-env.sh` to match your actual Ollama host.

## Gemini CLI Unavailable

**Problem:** Route returns "Gemini CLI not found on PATH"

**Fix:** The Gemini CLI (`gemini` binary) must be installed and on PATH for the gemini backend to work. If you do not have it, force a different backend:

```bash
LLM_BACKEND=local python cli.py "analyze this code"
```

Or set `LLM_BACKEND=local` in `.env`.

## OpenRouter Failures

**Problem:** Route returns "OPENROUTER_API_KEY is not set"

**Fix:** Set your key in `.env`:

```
OPENROUTER_API_KEY=sk-or-...
```

**Problem:** OpenRouter returns HTTP 4xx or 5xx

**Fix:** Check your API key, account balance, and the model name. The default model sent to OpenRouter is `openai/gpt-3.5-turbo`. The application will cascade to the offline fallback stub if OpenRouter also fails.

## Shell Commands Blocked

**Problem:** A shell step in a multi-step route returns "BLOCKED: Command not allowed"

**Reason:** `tools/shell.py` only allows `ls`, `pwd`, `whoami`, `date`, and `uname`. All other commands are blocked by the allowlist.

**Fix:** This is an intentional safety constraint. The allowlist is defined in `tools/shell.py` and cannot be overridden via config or environment variables in this version.

## Config Changes Not Affecting Model Selection

**Problem:** Updating the `models` section in `config/model_router.json` does not change which models are used

**Reason:** The `models` section in `config/model_router.json` is present but is not consumed by any implementation. Route-specific Ollama models are set by `MODEL_BY_ACTION` in `core/executor.py`. OpenRouter model is passed via the `model` argument to `_call_openrouter()`.

**Fix:** To change the Ollama model for a specific action, edit `MODEL_BY_ACTION` in `core/executor.py` (code change required). To override at runtime, set `OLLAMA_MODEL` in the environment before starting the server.

## Missing certifi Dependency

**Problem:** `ImportError: No module named 'certifi'` when tools/http.py is called

**Reason:** `certifi` is imported in `tools/http.py` but is not explicitly declared in `requirements.txt`. It is typically installed as a transitive dependency of `requests`, but this is not guaranteed across all environments.

**Fix:** Install certifi explicitly:

```bash
pip install certifi
```

Or add it to `requirements.txt` (code change required, not done in this pass).

## agents.server:app Launch Config Fails

**Problem:** The VS Code "Atlas API (agents.server:app)" launch config fails to start

**Reason:** `agents/server.py` does not exist. The `agents/` directory is an empty stub. This launch config is a placeholder for future development.

**Fix:** Use "Atlas API (main:app)" in VS Code, or run `bash scripts/run-api.sh` from the terminal.

## Smoke Test Fails

**Problem:** `bash scripts/smoke_test.sh` returns connection refused or empty response

**Fix:** The API must be running on port 8010 before running smoke_test.sh. Start it first:

```bash
bash scripts/run-api.sh
# in a separate terminal:
bash scripts/smoke_test.sh
```

**Problem:** `bash scripts/smoke.sh` fails at the pytest step

**Fix:** Activate the venv and run pytest directly to see the error:

```bash
source .venv/bin/activate
pytest -q
```
