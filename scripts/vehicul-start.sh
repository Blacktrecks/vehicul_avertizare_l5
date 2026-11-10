#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${APP_DIR}/logs"

mkdir -p "${LOG_DIR}"
cd "${APP_DIR}"

export PYTHONUNBUFFERED=1
export DJANGO_DEBUG="${DJANGO_DEBUG:-0}"
export DJANGO_ALLOWED_HOSTS="${DJANGO_ALLOWED_HOSTS:-*,localhost,127.0.0.1,[::1],0.0.0.0}"
export MCD_SIMULATE="${MCD_SIMULATE:-0}"

echo "[vehicul-start] starting app from ${APP_DIR}"
exec python3 manage.py runserver 0.0.0.0:8000
