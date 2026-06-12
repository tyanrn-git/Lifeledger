#!/usr/bin/env bash
# Перезапуск локального бота в конце работы агента, если менялся код бота.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

PENDING=".cursor/.bot-restart-pending"
if [[ ! -f "$PENDING" ]]; then
  exit 0
fi

if bash scripts/restart_bot_local.sh; then
  rm -f "$PENDING"
else
  echo "restart-bot-on-stop: restart failed, pending flag kept" >&2
  exit 1
fi

exit 0
