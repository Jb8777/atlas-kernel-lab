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
python cli.py "debug this fastapi endpoint"

API:
uvicorn main:app --reload --port 8000

## Local backend

Ollama must be running at:
http://localhost:11434

Example .env:
LLM_BACKEND=local
OLLAMA_MODEL=deepseek-coder:6.7b
OLLAMA_HOST=http://localhost:11434

## Tests
pytest -q

## Health check
curl http://127.0.0.1:8000/v1/health

## Route execution
curl -X POST http://127.0.0.1:8000/v1/route \
  -H "Content-Type: application/json" \
  -d '{"text":"debug this fastapi endpoint"}'
