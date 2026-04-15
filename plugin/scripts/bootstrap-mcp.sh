#!/usr/bin/env bash
set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$PLUGIN_DIR/.venv"
SERVER="$PLUGIN_DIR/mcp/server/server.py"

# Create venv if missing
if [ ! -f "$VENV_DIR/bin/python3" ]; then
    python3 -m venv "$VENV_DIR"
fi

# Install dependencies
"$VENV_DIR/bin/pip" install -q -r "$PLUGIN_DIR/requirements.txt" 2>/dev/null

# Exec server
export PYTHONPATH="$PLUGIN_DIR/mcp:${PYTHONPATH:-}"
exec "$VENV_DIR/bin/python3" "$SERVER" --mode stdio
