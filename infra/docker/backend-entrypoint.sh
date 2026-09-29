#!/bin/sh
# Backend container entrypoint
# Waits for DB then starts the requested command.
set -e

echo "[entrypoint] Starting Ticket backend..."
echo "[entrypoint] DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-config.settings}"

exec "$@"
