#!/usr/bin/env bash
# После git push ждёт готовности Railway (новый контейнер = перезапуск бота в проде).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

input="$(cat)"
command="$(printf '%s' "$input" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('command', ''))
" 2>/dev/null || true)"

if [[ ! "$command" =~ git[[:space:]]+push ]]; then
  exit 0
fi

bash scripts/wait_railway_deploy.sh

exit 0
