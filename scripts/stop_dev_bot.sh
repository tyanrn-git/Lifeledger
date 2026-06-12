#!/usr/bin/env bash
set -euo pipefail

LABEL="com.lifeledger.bot"
UID_NUM="$(id -u)"

launchctl bootout "gui/${UID_NUM}/${LABEL}" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/${LABEL}.plist"

if lsof -ti :8080 >/dev/null 2>&1; then
  lsof -ti :8080 | xargs kill 2>/dev/null || true
fi

echo "stop_dev_bot: launchd agent removed, port 8080 freed"
