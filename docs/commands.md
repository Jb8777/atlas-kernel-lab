# Commands

All commands below are confirmed from source files. Run from the repo root unless noted.

## Bootstrap

```bash
bash scripts/bootstrap.sh
```

Creates the virtualenv, installs requirements, copies `.env.example` to `.env` if absent.

## Start the API

Via script (recommended — sources dev-env.sh, activates venv, port 8010):

```bash
bash scripts/run-api.sh
```

Direct (venv must be active, env vars set):

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8010
```

## CLI

```bash
python cli.py "debug this fastapi endpoint"
python cli.py "hello"
python cli.py "research transformer architectures"
```

Output is a JSON object containing `routing`, `execution`, and `result` fields.

## API Health Check

```bash
curl http://127.0.0.1:8010/v1/health
```

## API Route Execution — Flat Text

```bash
curl -X POST http://127.0.0.1:8010/v1/route \
  -H "Content-Type: application/json" \
  -d '{"text":"debug this fastapi endpoint"}'
```

## API Route Execution — Structured Payload

```bash
curl -X POST http://127.0.0.1:8010/v1/route \
  -H "Content-Type: application/json" \
  -d '{
    "task": "debug FastAPI endpoint",
    "code": "@app.get(\\"/users/{id}\\")
async def get_user(id: int):
    user = fetch_user(id)
    return user.name",
    "error": "500 Internal Server Error",
    "goal": "return valid JSON"
  }'
```

## Smoke Tests (Smoke.sh — no live API required)

```bash
bash scripts/smoke.sh
```

Runs:
1. `pytest -q`
2. `python cli.py "debug this fastapi endpoint"`
3. `python cli.py "hello"`
4. `python -c "from main import app; print(app.title)"`

## Smoke Test (smoke_test.sh — requires running API on port 8010)

```bash
bash scripts/smoke_test.sh
```

POSTs `scripts/smoke_payload.json` to `http://127.0.0.1:8010/v1/route`.

## Unit Tests

```bash
pytest -q
```

## VS Code Tasks (Ctrl+Shift+B or Run Task)

| Task | What it runs |
|------|-------------|
| Atlas: Smoke test | `bash scripts/smoke_test.sh` |
| Atlas: Test | `pytest -q` |
| Atlas: Ollama tags | `curl -s http://127.0.0.1:11434/api/tags` (lists available models) |

## Check Ollama Models

```bash
curl -s http://127.0.0.1:11434/api/tags | python -m json.tool | sed -n '1,80p'
```

## Override Backend via Environment Variable

```bash
LLM_BACKEND=openrouter python cli.py "explain async/await"
LLM_BACKEND=gemini python cli.py "compare BERT and GPT"
LLM_BACKEND=fallback python cli.py "test fallback"
```

## Dev Environment Variables (sourced by run-api.sh)

```bash
source scripts/dev-env.sh
```

Exports: `LLM_BACKEND=local`, `OLLAMA_MODEL=deepseek-coder:6.7b`, `OLLAMA_HOST=http://127.0.0.1:11434`, `PYTHONUNBUFFERED=1`, `LLM_TIMEOUT_S=120`.
