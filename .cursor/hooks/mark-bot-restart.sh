#!/usr/bin/env bash
# Помечает, что после сессии агента нужен перезапуск бота.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

input="$(cat)"
file_path="$(printf '%s' "$input" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for key in ('file_path', 'path', 'file'):
    v = data.get(key)
    if v:
        print(v)
        break
" 2>/dev/null || true)"

if [[ -z "$file_path" ]]; then
  exit 0
fi

case "$file_path" in
  app/*|app/db/migrations/*|requirements.txt|Dockerfile|railway.toml)
    mkdir -p .cursor
    touch .cursor/.bot-restart-pending
    ;;
esac

exit 0
