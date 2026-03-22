#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

echo "=== TESTS ==="
pytest -q

echo
echo "=== CLI CODE ==="
python cli.py "debug this fastapi endpoint"

echo
echo "=== CLI GENERAL ==="
python cli.py "hello"

echo
echo "=== API IMPORT ==="
python -c "from main import app; print(app.title)"
