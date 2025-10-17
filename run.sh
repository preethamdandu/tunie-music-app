#!/usr/bin/env bash

# Robust startup for Streamlit: prefer 8501, fall back to 8502 if busy

set -euo pipefail

APP="app.py"
PORT_1=8501
PORT_2=8502

is_port_in_use() {
  lsof -i tcp:$1 >/dev/null 2>&1 || nc -z localhost $1 >/dev/null 2>&1 || return 1
}

echo "Starting TuneGenie..."

if is_port_in_use "$PORT_1"; then
  echo "Warning: Port $PORT_1 is already in use. Launching on $PORT_2 instead."
  exec streamlit run "$APP" --server.headless true --server.port "$PORT_2"
else
  exec streamlit run "$APP" --server.headless true --server.port "$PORT_1"
fi


