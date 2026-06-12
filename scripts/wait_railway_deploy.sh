#!/usr/bin/env bash
# Ждёт готовности Railway после push (healthcheck /health).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DOMAIN="${RAILWAY_PUBLIC_DOMAIN:-}"
if [[ -z "$DOMAIN" && -f .env ]]; then
  line="$(grep -E '^RAILWAY_PUBLIC_DOMAIN=' .env 2>/dev/null | tail -1 || true)"
  if [[ -n "$line" ]]; then
    DOMAIN="${line#RAILWAY_PUBLIC_DOMAIN=}"
    DOMAIN="${DOMAIN%\"}"
    DOMAIN="${DOMAIN#\"}"
  fi
fi
if [[ -z "$DOMAIN" ]]; then
  line="$(grep -E '^WEBHOOK_URL=' .env 2>/dev/null | tail -1 || true)"
  if [[ -n "$line" ]]; then
    url="${line#WEBHOOK_URL=}"
    url="${url%\"}"
    url="${url#\"}"
    DOMAIN="$(echo "$url" | sed -E 's#^https?://([^/]+)/.*#\1#')"
  fi
fi
if [[ -z "$DOMAIN" ]]; then
  DOMAIN="lifeledger-production-c53d.up.railway.app"
fi

DOMAIN="${DOMAIN#https://}"
DOMAIN="${DOMAIN#http://}"
DOMAIN="${DOMAIN%/}"
URL="https://${DOMAIN}/health"

TRIES="${RAILWAY_DEPLOY_WAIT_TRIES:-36}"
SLEEP="${RAILWAY_DEPLOY_WAIT_SLEEP:-10}"

echo "wait_railway_deploy: polling $URL (max $((TRIES * SLEEP))s)"

for ((i = 1; i <= TRIES; i++)); do
  if response="$(curl -fsS --max-time 15 "$URL" 2>/dev/null)" && [[ "$response" == "ok" ]]; then
    echo "wait_railway_deploy: ready after ${i} attempt(s)"
    exit 0
  fi
  echo "wait_railway_deploy: attempt $i/$TRIES not ready, sleep ${SLEEP}s"
  sleep "$SLEEP"
done

echo "wait_railway_deploy: timeout — check Railway dashboard" >&2
exit 1
