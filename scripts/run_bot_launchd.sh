#!/usr/bin/env bash
# Обёртка для launchd. .env читает pydantic в app.config (WorkingDirectory = корень проекта).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec "$ROOT/.venv/bin/python" -m app.main
