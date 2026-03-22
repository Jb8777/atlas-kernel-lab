#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

curl -s -X POST http://127.0.0.1:8010/v1/route \
  -H "Content-Type: application/json" \
  -d @scripts/smoke_payload.json

echo
