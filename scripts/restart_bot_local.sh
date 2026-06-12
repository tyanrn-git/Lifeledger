#!/usr/bin/env bash
# Запуск / перезапуск локального бота.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PORT="${PORT:-8080}"
PID_FILE=".cursor/bot.pid"
LOG_FILE=".cursor/bot.log"
LOCK_FILE=".cursor/bot-restart.lock"
LABEL="com.lifeledger.bot"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"

if [[ -f .env ]]; then
  line="$(grep -E '^PORT=' .env 2>/dev/null | tail -1 || true)"
  if [[ -n "$line" ]]; then
    PORT="${line#PORT=}"
    PORT="${PORT%\"}"
    PORT="${PORT#\"}"
  fi
fi

mkdir -p .cursor

bot_healthy() {
  curl -fsS --max-time 2 "http://127.0.0.1:${PORT}/health" 2>/dev/null | grep -q ok
}

launchd_installed() {
  [[ -f "$PLIST" ]] && launchctl print "gui/$(id -u)/${LABEL}" &>/dev/null
}

if bot_healthy; then
  echo "restart_bot_local: already running on port $PORT"
  exit 0
fi

# launchd (если установлен через install_dev_bot.sh)
if launchd_installed; then
  echo "restart_bot_local: launchd kickstart"
  launchctl kickstart -k "gui/$(id -u)/${LABEL}" 2>/dev/null || true
  for ((i = 1; i <= 25; i++)); do
    if bot_healthy; then
      echo "restart_bot_local: health ok (launchd)"
      exit 0
    fi
    sleep 2
  done
  echo "restart_bot_local: launchd не поднял бота, пробуем вручную…" >&2
fi

now=$(date +%s)
if [[ -f "$LOCK_FILE" ]]; then
  last=$(cat "$LOCK_FILE" 2>/dev/null || echo 0)
  if (( now - last < 5 )); then
    bash "$ROOT/scripts/start_bot_local.sh"
    exit 0
  fi
fi
echo "$now" > "$LOCK_FILE"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    kill "$old_pid" 2>/dev/null || true
    sleep 1
  fi
fi

if command -v lsof >/dev/null 2>&1; then
  pids="$(lsof -ti :"$PORT" 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    sleep 1
  fi
fi

bash "$ROOT/scripts/start_bot_local.sh"
