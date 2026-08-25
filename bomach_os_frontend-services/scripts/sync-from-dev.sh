#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROD_ROOT="$(cd "$SCRIPT_DIR/../../../bomach_os_frontend/services" && pwd)"

MODE="sync"
RSYNC_FLAGS=(-a --delete)

if [[ "${1:-}" == "--dry-run" ]]; then
  MODE="dry-run"
  RSYNC_FLAGS+=(--dry-run --itemize-changes)
fi

if [[ ! -d "$PROD_ROOT" ]]; then
  echo "Production frontend not found: $PROD_ROOT" >&2
  echo "Expected layout: bomach/{test/bomach_os_frontend-services,bomach_os_frontend/services}" >&2
  exit 1
fi

if [[ ! -d "$TEST_ROOT" ]]; then
  echo "Test frontend not found: $TEST_ROOT" >&2
  exit 1
fi

echo "Source:      $PROD_ROOT"
echo "Destination: $TEST_ROOT"
echo "Mode:        $MODE"
echo

rsync \
  "${RSYNC_FLAGS[@]}" \
  --exclude '.git/' \
  --exclude 'node_modules/' \
  --exclude 'dist/' \
  --exclude 'coverage/' \
  --exclude '.vite/' \
  --exclude '.turbo/' \
  --exclude 'storybook-static/' \
  --exclude 'scripts/sync-from-dev.sh' \
  "$PROD_ROOT/" \
  "$TEST_ROOT/"

echo
echo "Sync complete."
