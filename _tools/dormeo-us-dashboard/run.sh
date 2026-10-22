#!/usr/bin/env bash
# Rebuild the Dormeo US dashboard from data/ + raw/ and the latest FSG inventory/reconciliation pages.
# Run from anywhere after the day's Sellerise pulls have been saved with update_data.py (see RUNBOOK.md).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; REPO="$(cd "$HERE/../.." && pwd)"
cd "$HERE"
python3 parse_sheet_pages.py "$REPO" data
python3 update_data.py finalize
python3 render.py template.html data "$REPO/dormeo-us/index.html.new"
python3 validate.py "$REPO/dormeo-us/index.html.new"
mv "$REPO/dormeo-us/index.html.new" "$REPO/dormeo-us/index.html"
echo "BUILD_OK"
