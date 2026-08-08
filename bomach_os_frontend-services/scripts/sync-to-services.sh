#!/usr/bin/env bash
# Sync production-ready code from this development workspace into
# ../../bomach_os_frontend/services (the GitHub-bound repo).
#
# Usage:
#   npm run sync
#   npm run sync -- --dry-run
#   npm run sync -- --with-readme
#
# Does NOT commit or push. Review `git status` in the destination after syncing.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$(cd "$SCRIPT_DIR/.." && pwd)"
DEST="$(cd "$SRC/../../bomach_os_frontend/services" && pwd)"
EXCLUDES="$SCRIPT_DIR/sync.excludes"

DRY_RUN=0
WITH_README=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --with-readme) WITH_README=1 ;;
    -h|--help)
      sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      echo "Use --dry-run or --with-readme" >&2
      exit 1
      ;;
  esac
done

if [[ ! -d "$DEST/.git" ]]; then
  echo "Destination is missing a git repo: $DEST" >&2
  exit 1
fi

if [[ ! -f "$EXCLUDES" ]]; then
  echo "Missing excludes file: $EXCLUDES" >&2
  exit 1
fi

RSYNC=(rsync -a)
if [[ "$DRY_RUN" -eq 1 ]]; then
  RSYNC+=(--dry-run --itemize-changes)
fi

echo "Source:      $SRC"
echo "Destination: $DEST"
[[ "$DRY_RUN" -eq 1 ]] && echo "Mode:        dry-run"
echo

# Preserve production package identity before overwriting package.json
DEST_NAME="bomach-os-services"
DEST_VERSION="0.1.0"
if [[ -f "$DEST/package.json" ]]; then
  DEST_NAME="$(node -p "require('$DEST/package.json').name" 2>/dev/null || echo "$DEST_NAME")"
  DEST_VERSION="$(node -p "require('$DEST/package.json').version" 2>/dev/null || echo "$DEST_VERSION")"
fi

# 1) Application source — delete dest files removed from src (keeps trees aligned)
"${RSYNC[@]}" --delete \
  --exclude-from="$EXCLUDES" \
  "$SRC/src/" "$DEST/src/"

# 2) Tooling / public assets (no --delete on repo root)
ROOT_FILES=(
  index.html
  vite.config.ts
  vitest.config.ts
  tsconfig.json
  tsconfig.app.json
  tsconfig.node.json
  eslint.config.js
  prettier.config.mjs
  .prettierignore
  .editorconfig
  .gitignore
  .env.example
  package.json
  package-lock.json
)

for file in "${ROOT_FILES[@]}"; do
  if [[ -e "$SRC/$file" ]]; then
    "${RSYNC[@]}" "$SRC/$file" "$DEST/$file"
  fi
done

if [[ -d "$SRC/public" ]]; then
  "${RSYNC[@]}" --delete --exclude-from="$EXCLUDES" "$SRC/public/" "$DEST/public/"
fi

if [[ -d "$SRC/.vscode" ]]; then
  "${RSYNC[@]}" "$SRC/.vscode/" "$DEST/.vscode/"
fi

# 3) Curated docs only (standards / architecture — not session changelogs)
DOC_PATHS=(
  docs/architecture/Bomach_Service_Operations_Module_Architecture.md
  docs/api-integration/API_Integration_Standard.md
  docs/api-integration/Missing_Backend_Contracts.md
  docs/error-handling-and-feedback.md
  docs/design-system.md
  docs/authentication/implementation.md
  docs/ui-rebuild/standards/CSS_Architecture_Standard.md
  docs/roadmap/README.md
  docs/roadmap/Bomach_Service_Operations_Revised_Product_Phases.md
)

for rel in "${DOC_PATHS[@]}"; do
  if [[ -f "$SRC/$rel" ]]; then
    mkdir -p "$DEST/$(dirname "$rel")"
    "${RSYNC[@]}" "$SRC/$rel" "$DEST/$rel"
  fi
done

if [[ "$WITH_README" -eq 1 && -f "$SRC/README.md" ]]; then
  "${RSYNC[@]}" "$SRC/README.md" "$DEST/README.md"
fi

# 4) Restore production package identity + strip Storybook-only scripts
if [[ "$DRY_RUN" -eq 0 ]]; then
  node <<EOF
const fs = require('node:fs')
const path = '$DEST/package.json'
const pkg = JSON.parse(fs.readFileSync(path, 'utf8'))
pkg.name = '$DEST_NAME'
pkg.version = '$DEST_VERSION'
delete pkg.scripts.storybook
delete pkg.scripts['build:storybook']
pkg.scripts.check =
  'npm run typecheck && npm run lint && npm run format:check && npm run build'
pkg.scripts.sync =
  'bash scripts/sync-from-dev.sh'
fs.writeFileSync(path, JSON.stringify(pkg, null, 2) + '\n')
EOF
fi

echo
echo "Sync complete."
if [[ "$DRY_RUN" -eq 0 ]]; then
  echo
  echo "Destination git status:"
  git -C "$DEST" status -sb
  echo
  echo "Next:"
  echo "  cd $DEST"
  echo "  git add -A && git status"
  echo "  git commit -m \"…\"   # when ready"
  echo "  git push"
fi
