#!/usr/bin/env bash
set -e

PYTHON_BIN="${PYTHON_BIN:-python3}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
SYSTEM_INSTALL=0

for arg in "$@"; do
    if [ "$arg" = "--system" ]; then
        SYSTEM_INSTALL=1
    fi
done

if [ "$SYSTEM_INSTALL" -eq 1 ]; then
    "$PYTHON_BIN" -m pip install -r "$SCRIPT_DIR/requirements.txt" --break-system-packages
    "$PYTHON_BIN" -m pip install "$SCRIPT_DIR" --break-system-packages
    echo "Installed system wide. Run with: uartsync"
else
    if [ ! -d "$VENV_DIR" ]; then
        "$PYTHON_BIN" -m venv "$VENV_DIR"
    fi
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
    "$VENV_DIR/bin/pip" install "$SCRIPT_DIR"
    echo "Installed. Run with: $VENV_DIR/bin/uartsync"
    echo "If your system blocks pip with an externally managed environment error, rerun with: ./install.sh --system"
fi
