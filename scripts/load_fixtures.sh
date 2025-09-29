#!/bin/sh
set -e
echo "Loading fixtures: vehicles.json"
uv run python manage.py loaddata eld_system/fixtures/vehicles.json || true
