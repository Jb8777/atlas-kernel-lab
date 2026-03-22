#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

export LLM_BACKEND=local
export OLLAMA_MODEL=deepseek-coder:6.7b
export OLLAMA_HOST=http://127.0.0.1:11434

uvicorn main:app --reload --host 127.0.0.1 --port 8010
