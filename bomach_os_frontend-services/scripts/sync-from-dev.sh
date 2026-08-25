#!/usr/bin/env bash
# Thin wrapper: pull latest production-ready files from the development workspace.
# Prefer running `npm run sync` from the test/dev repo; this exists for convenience
# when you are already inside the GitHub-bound services repo.
#
# Usage:
#   npm run sync
#   npm run sync -- --dry-run

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEV_SCRIPT="$(cd "$SCRIPT_DIR/../../../test/bomach_os_frontend-services/scripts" && pwd)/sync-to-services.sh"

if [[ ! -x "$DEV_SCRIPT" && -f "$DEV_SCRIPT" ]]; then
  chmod +x "$DEV_SCRIPT"
fi

if [[ ! -f "$DEV_SCRIPT" ]]; then
  echo "Dev sync script not found at: $DEV_SCRIPT" >&2
  echo "Expected layout: bomach/{test/bomach_os_frontend-services,bomach_os_frontend/services}" >&2
  exit 1
fi

exec bash "$DEV_SCRIPT" "$@"
