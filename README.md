# AtlasKernel

AtlasKernel is a local-first prompt routing and execution engine.

## Features

- Route classification: code, research, ops, general
- Execution planning
- CLI entrypoint
- FastAPI app entrypoint
- Local LLM support via Ollama
- Optional cloud backend support via OpenRouter
- Multi-step execution support (then, if, else, repeat)

## Entrypoints

CLI:
```
python cli.py "debug this fastapi endpoint"
```

API:
```
bash scripts/run-api.sh
```

> **Port note:** The development API runs on port **8010**. The commands below and in the README use port 8010.

## Local backend

Ollama must be running at: http://localhost:11434

Example .env:

```
LLM_BACKEND=local
OLLAMA_MODEL=deepseek-coder:6.7b
OLLAMA_HOST=http://localhost:11434
```

## Bootstrap

```
bash scripts/bootstrap.sh
```

## Tests

```
pytest -q
```

## Health check

```
curl http://127.0.0.1:8010/v1/health
```

## Route execution

```
curl -X POST http://127.0.0.1:8010/v1/route \
  -H "Content-Type: application/json" \
  -d '{"text":"debug this fastapi endpoint"}'
```

## Documentation

- [Overview](docs/overview.md) — purpose, key modules, entrypoints, role in stack, how it relates to atlas-kernel-clean
- [Setup](docs/setup.md) — prerequisites, bootstrap, env vars, API startup, VS Code harness, tests
- [Commands](docs/commands.md) — all confirmed commands and scripts
- [Architecture](docs/architecture.md) — module reference, request lifecycle, config drift, safety boundaries
- [Troubleshooting](docs/troubleshooting.md) — bootstrap failures, env issues, Ollama/OpenRouter/Gemini, shell allowlist, known gaps
