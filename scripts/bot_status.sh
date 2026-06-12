#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PORT="${PORT:-8080}"
PID_FILE=".cursor/bot.pid"

if [[ -f .env ]]; then
  line="$(grep -E '^PORT=' .env 2>/dev/null | tail -1 || true)"
  if [[ -n "$line" ]]; then
    PORT="${line#PORT=}"
    PORT="${PORT%\"}"
    PORT="${PORT#\"}"
  fi
fi

bot_healthy() {
  curl -fsS --max-time 2 "http://127.0.0.1:${PORT}/health" 2>/dev/null | grep -q ok
}

if bot_healthy; then
  pid="$(lsof -ti :"$PORT" 2>/dev/null | head -1 || true)"
  echo "process: running pid=${pid:-?}"
else
  echo "process: not running"
fi

if curl -fsS --max-time 2 "http://127.0.0.1:${PORT}/health" 2>/dev/null | grep -q ok; then
  echo "health: ok (http://127.0.0.1:${PORT}/health)"
  echo "admin:  http://127.0.0.1:${PORT}/admin"
else
  echo "health: down — run: bash scripts/start_bot_local.sh"
  exit 1
fi
