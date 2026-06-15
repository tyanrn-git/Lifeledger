#!/usr/bin/env bash
# Полный QA: unit/route tests + опциональный HTTP smoke.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

echo "=== pytest ==="
"$PYTHON" -m pytest tests/ -q --tb=short "$@"
echo ""

echo "=== HTTP smoke (prod default) ==="
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source <(grep -E '^(ADMIN_PASSWORD|SMOKE_BASE_URL|RAILWAY_PUBLIC_DOMAIN)=' .env 2>/dev/null | sed 's/^/export /') || true
  set +a
fi
if [[ -z "${SMOKE_BASE_URL:-}" && -n "${RAILWAY_PUBLIC_DOMAIN:-}" ]]; then
  export SMOKE_BASE_URL="https://${RAILWAY_PUBLIC_DOMAIN#https://}"
fi
"$PYTHON" scripts/smoke_http.py ${SMOKE_BASE_URL:+--base "$SMOKE_BASE_URL"}
echo ""
echo "QA done."
