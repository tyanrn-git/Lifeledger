#!/usr/bin/env bash
# Запуск бота в текущем терминале (рекомендуется для разработки).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PORT="${PORT:-8080}"
if [[ -f .env ]]; then
  line="$(grep -E '^PORT=' .env 2>/dev/null | tail -1 || true)"
  if [[ -n "$line" ]]; then
    PORT="${line#PORT=}"
    PORT="${PORT%\"}"
    PORT="${PORT#\"}"
  fi
fi

if curl -fsS --max-time 2 "http://127.0.0.1:${PORT}/health" 2>/dev/null | grep -q ok; then
  pid="$(lsof -ti :"$PORT" 2>/dev/null | head -1 || true)"
  echo "Бот уже запущен на порту ${PORT} (pid=${pid:-?})."
  echo "  health: http://127.0.0.1:${PORT}/health"
  echo "  admin:  http://127.0.0.1:${PORT}/admin"
  echo ""
  echo "Перезапуск: bash scripts/restart_bot_local.sh"
  exit 0
fi

if command -v lsof >/dev/null 2>&1; then
  pids="$(lsof -ti :"$PORT" 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    echo "Порт ${PORT} занят (pid: $pids), но /health не отвечает." >&2
    echo "Освободить: kill $pids" >&2
    exit 1
  fi
fi

echo "Starting bot on port ${PORT}… (Ctrl+C to stop)"
exec .venv/bin/python -m app.main
