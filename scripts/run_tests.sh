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

MODULES=(
  "services/collector-gateway"
  "services/data-cleaner"
  "services/data-lake-writer"
  "services/feature-pipeline"
  "services/strategy-engine"
  "services/opportunity-aggregator"
  "services/risk-guard"
  "services/signal-api"
  "services/signal-streamer"
  "services/backtest-service"
)

echo "==> compileall checks"
for module in "${MODULES[@]}"; do
  echo "  -> python -m compileall $module"
  python -m compileall "$module" >/dev/null
done

echo "==> running pytest suites"
pytest services/collector-gateway/tests \
       services/data-cleaner/tests \
       services/data-lake-writer/tests \
       services/feature-pipeline/tests \
       services/strategy-engine/tests \
       services/opportunity-aggregator/tests \
       services/signal-api/tests \
       services/backtest-service/tests

echo "All tests completed successfully."
