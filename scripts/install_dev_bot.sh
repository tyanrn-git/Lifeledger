#!/usr/bin/env bash
# Установка launchd-агента: бот держится живым и перезапускается macOS автоматически.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.lifeledger.bot"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
RUNNER="$ROOT/scripts/run_bot_launchd.sh"
LOG="$ROOT/.cursor/bot.log"
ENV_FILE="$ROOT/.env"

if [[ "$(uname)" != "Darwin" ]]; then
  echo "install_dev_bot: только macOS (launchd)" >&2
  exit 1
fi

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "install_dev_bot: .venv not found" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "install_dev_bot: .env not found" >&2
  exit 1
fi

chmod +x "$RUNNER"
mkdir -p "$ROOT/.cursor" "$HOME/Library/LaunchAgents"

launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true

# Переменные из .env → plist (launchd не всегда читает .env из Documents)
ENV_PLIST=""
while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line%%#*}"
  line="$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -z "$line" ]] && continue
  [[ "$line" != *=* ]] && continue
  key="${line%%=*}"
  val="${line#*=}"
  val="${val%\"}"; val="${val#\"}"
  val="${val%\'}"; val="${val#\'}"
  val="${val//&/&amp;}"
  val="${val//</&lt;}"
  val="${val//>/&gt;}"
  ENV_PLIST="${ENV_PLIST}    <key>${key}</key>
    <string>${val}</string>
"
done < "$ENV_FILE"

cat >"$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${RUNNER}</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${ROOT}</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${LOG}</string>
  <key>StandardErrorPath</key>
  <string>${LOG}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/usr/local/bin:/usr/bin:/bin:${ROOT}/.venv/bin</string>
${ENV_PLIST}  </dict>
</dict>
</plist>
EOF

launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/${LABEL}"
launchctl kickstart -k "gui/$(id -u)/${LABEL}"

echo "install_dev_bot: launchd agent installed (env from .env)"
echo "  log: $LOG"

for ((i = 1; i <= 40; i++)); do
  if curl -fsS --max-time 2 "http://127.0.0.1:8080/health" 2>/dev/null | grep -q ok; then
    echo "install_dev_bot: health ok"
    exit 0
  fi
  sleep 2
done

echo "install_dev_bot: slow start — see $LOG" >&2
tail -20 "$LOG" >&2 || true
exit 1
