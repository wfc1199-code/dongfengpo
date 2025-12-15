#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  echo "Loading environment variables from .env"
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export PYTHONPATH="${ROOT_DIR}/libs/data_contracts:${PYTHONPATH:-}"

PID_FILE="${ROOT_DIR}/pipeline-services.pid"

if [[ -f "$PID_FILE" ]]; then
  echo "Existing $PID_FILE detected. Remove it before启动或使用 kill \$(cat $PID_FILE)." >&2
  exit 1
fi

SERVICES=(
  "collector_gateway.main"
  "stream_buffer.main"
  "data_cleaner.main"
  "data_lake_writer.main"
  "feature_pipeline.main"
  "strategy_engine.main"
  "opportunity_aggregator.main"
  "risk_guard.main"
  "signal_api.main"
  "signal_streamer.main"
  "backtest_service.main"
)

touch "$PID_FILE"

cleanup() {
  echo "\nStopping services..."
  if [[ -s "$PID_FILE" ]]; then
    while read -r pid module; do
      if kill -0 "$pid" 2>/dev/null; then
        echo "  -> killing $module (pid=$pid)"
        kill "$pid" 2>/dev/null || true
      fi
    done < "$PID_FILE"
  fi
  rm -f "$PID_FILE"
}

trap cleanup EXIT INT TERM

echo "Starting data pipeline services..."

for module in "${SERVICES[@]}"; do
  echo "  -> launching $module"
  python -m "$module" &
  pid=$!
  echo "$pid $module" >> "$PID_FILE"
  sleep 1
done

echo "All services started. Press Ctrl+C to stop."

wait
