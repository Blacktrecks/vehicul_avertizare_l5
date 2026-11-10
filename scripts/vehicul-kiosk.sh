#!/usr/bin/env bash
set -euo pipefail

APP_URL="${APP_URL:-http://127.0.0.1:8000/}"

for browser in chromium chromium-browser google-chrome google-chrome-stable; do
  if command -v "$browser" >/dev/null 2>&1; then
    BROWSER="$browser"
    break
  fi
done

if [[ -z "${BROWSER:-}" ]]; then
  echo "[vehicul-kiosk] no supported browser found (chromium / google-chrome)" >&2
  exit 1
fi

export DISPLAY="${DISPLAY:-:0}"

# disable screen blanking for kiosk mode
if command -v xset >/dev/null 2>&1; then
  xset s off || true
  xset -dpms || true
  xset s noblank || true
fi

for _ in $(seq 1 60); do
  if curl -fsS "${APP_URL}" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

exec "$BROWSER" \
  --kiosk \
  --disable-infobars \
  --noerrdialogs \
  --disable-session-crashed-bubble \
  --disable-features=TranslateUI \
  --autoplay-policy=no-user-gesture-required \
  --user-data-dir=/tmp/vehicul-kiosk \
  "${APP_URL}"
