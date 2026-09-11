#!/usr/bin/env bash
# ==============================================================================
# LUNAR CORRESPONDENCE AI — Production Server Launch Script
# ==============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

PYTHON_BIN="/opt/anaconda3/bin/python3"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

export PORT="${PORT:-5050}"
export LUNAR_SECRET_KEY="${LUNAR_SECRET_KEY:-chandrayaan2-telemetry-secret-key}"

echo "------------------------------------------------------------"
echo "  Starting LUNAR CORRESPONDENCE AI Operational Server"
echo "  Endpoint: http://localhost:${PORT}"
echo "------------------------------------------------------------"

exec "$PYTHON_BIN" backend/app.py
