#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROD_ROOT="$(cd "$SCRIPT_DIR/../../../bomach_os_backend" && pwd)"

MODE="sync"
RSYNC_FLAGS=(-a --delete)

if [[ "${1:-}" == "--dry-run" ]]; then
  MODE="dry-run"
  RSYNC_FLAGS+=(--dry-run --itemize-changes)
fi

if [[ ! -d "$PROD_ROOT" ]]; then
  echo "Production backend not found: $PROD_ROOT" >&2
  echo "Expected layout: bomach/{test/bomach_os_backend,bomach_os_backend}" >&2
  exit 1
fi

if [[ ! -d "$TEST_ROOT" ]]; then
  echo "Test backend not found: $TEST_ROOT" >&2
  exit 1
fi

echo "Source:      $PROD_ROOT"
echo "Destination: $TEST_ROOT"
echo "Mode:        $MODE"
echo

rsync \
  "${RSYNC_FLAGS[@]}" \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.pytest_cache/' \
  --exclude '.mypy_cache/' \
  --exclude '.ruff_cache/' \
  --exclude 'htmlcov/' \
  --exclude '.coverage' \
  --exclude 'coverage.xml' \
  --exclude 'media/' \
  --exclude 'mediafiles/' \
  --exclude 'staticfiles/' \
  --exclude 'db.sqlite3' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude 'sync' \
  --exclude 'sync-prod' \
  --exclude 'scripts/sync-to-prod.sh' \
  --exclude 'scripts/sync-from-dev.sh' \
  "$PROD_ROOT/" \
  "$TEST_ROOT/"

echo
echo "Sync complete."
