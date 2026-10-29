#!/bin/sh
set -eu

# Migrations run separately during deployment with a different database role.
python /app/scripts/check_runtime.py --wait
exec python -u /app/main.py
