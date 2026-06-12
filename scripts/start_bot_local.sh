#!/usr/bin/env bash
# Запуск бота, если ещё не работает (не убивает работающий процесс).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PORT="${PORT:-8080}"
PID_FILE=".cursor/bot.pid"
LOG_FILE=".cursor/bot.log"
PYTHON="${ROOT}/.venv/bin/python"

if [[ -f .env ]]; then
  line="$(grep -E '^PORT=' .env 2>/dev/null | tail -1 || true)"
  if [[ -n "$line" ]]; then
    PORT="${line#PORT=}"
    PORT="${PORT%\"}"
    PORT="${PORT#\"}"
  fi
fi

if [[ ! -x "$PYTHON" ]]; then
  echo "start_bot_local: .venv not found" >&2
  exit 1
fi

mkdir -p .cursor

bot_healthy() {
  curl -fsS --max-time 2 "http://127.0.0.1:${PORT}/health" 2>/dev/null | grep -q ok
}

if bot_healthy; then
  pid="$(lsof -ti :"$PORT" 2>/dev/null | head -1 || true)"
  echo "start_bot_local: already running pid=${pid:-?} port=$PORT"
  exit 0
fi

# Порт занят мёртвым процессом — освободить
if command -v lsof >/dev/null 2>&1; then
  pids="$(lsof -ti :"$PORT" 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    sleep 1
  fi
fi

{
  echo "===== start $(date -Iseconds) ====="
} >>"$LOG_FILE"

# Отдельный subshell + disown: переживает завершение сессии Cursor
bash -c "cd '$ROOT' && exec '$PYTHON' -m app.main" >>"$LOG_FILE" 2>&1 &
new_pid=$!
disown "$new_pid" 2>/dev/null || true

echo "$new_pid" > "$PID_FILE"
echo "start_bot_local: started pid=$new_pid port=$PORT"
echo "start_bot_local: надёжнее — отдельный терминал: bash scripts/run_bot.sh"

for ((i = 1; i <= 30; i++)); do
  if ! kill -0 "$new_pid" 2>/dev/null; then
    echo "start_bot_local: exited — see $LOG_FILE" >&2
    tail -20 "$LOG_FILE" >&2 || true
    exit 1
  fi
  if curl -fsS --max-time 2 "http://127.0.0.1:${PORT}/health" 2>/dev/null | grep -q ok; then
    echo "start_bot_local: health ok"
    exit 0
  fi
  sleep 2
done

echo "start_bot_local: slow start, check $LOG_FILE" >&2
exit 0
