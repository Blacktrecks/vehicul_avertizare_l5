#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
USERNAME="${SUDO_USER:-$(id -un)}"
USER_HOME="$(getent passwd "${USERNAME}" | cut -d: -f6)"

SERVICE_SRC="${SCRIPT_DIR}/vehicul-alert.service"
SERVICE_DST="/etc/systemd/system/vehicul-alert.service"
KIOSK_SRC="${SCRIPT_DIR}/vehicul-kiosk.service"
KIOSK_DST="/etc/systemd/system/vehicul-kiosk.service"

if [[ ! -f "${SERVICE_SRC}" ]]; then
  echo "Missing service template: ${SERVICE_SRC}"
  exit 1
fi

if [[ ! -f "${KIOSK_SRC}" ]]; then
  echo "Missing kiosk template: ${KIOSK_SRC}"
  exit 1
fi

TMP_SERVICE="$(mktemp)"
TMP_KIOSK="$(mktemp)"

sed -e "s|__USER__|${USERNAME}|g" -e "s|__APP_DIR__|${REPO_DIR}|g" "${SERVICE_SRC}" > "${TMP_SERVICE}"
sed -e "s|__USER__|${USERNAME}|g" -e "s|__APP_DIR__|${REPO_DIR}|g" -e "s|__USER_HOME__|${USER_HOME}|g" "${KIOSK_SRC}" > "${TMP_KIOSK}"

sudo install -m 0644 "${TMP_SERVICE}" "${SERVICE_DST}"
sudo install -m 0644 "${TMP_KIOSK}" "${KIOSK_DST}"
rm -f "${TMP_SERVICE}" "${TMP_KIOSK}"

sudo systemctl daemon-reload
sudo systemctl enable vehicul-alert.service
sudo systemctl enable vehicul-kiosk.service
sudo systemctl restart vehicul-alert.service || true
sudo systemctl restart vehicul-kiosk.service || true
sudo systemctl status vehicul-alert.service vehicul-kiosk.service --no-pager || true
