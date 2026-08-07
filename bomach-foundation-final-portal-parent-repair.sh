#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ! -f package.json ]] || ! grep -q '"name": "bomach_os_frontend-services"' package.json; then
  echo "Error: run this from bomach_os_frontend-services."
  exit 1
fi

cat > src/routes/portal.tsx <<'EOF'
import { createFileRoute, redirect } from '@tanstack/react-router'

/**
 * The Client Portal is a separate application.
 *
 * This legacy parent route remains only so old internal bookmarks fail safely
 * inside the staff application instead of mounting client-owned UI.
 */
export const Route = createFileRoute('/portal')({
  beforeLoad: () => {
    return redirect({
      to: '/app/dashboard',
      replace: true,
    })
  },
  component: () => null,
})
EOF

echo "Checking for stale Client Portal / frontend-role authorization references..."

if grep -R "ClientPortalLayout" src --include='*.ts' --include='*.tsx'; then
  echo "ERROR: ClientPortalLayout is still referenced."
  exit 1
fi

if grep -R "clientPortalNavigation" src --include='*.ts' --include='*.tsx'; then
  echo "ERROR: clientPortalNavigation is still referenced."
  exit 1
fi

if grep -R "portalRead" src --include='*.ts' --include='*.tsx'; then
  echo "ERROR: portalRead is still referenced."
  exit 1
fi

if grep -R "rolePermissions" src --include='*.ts' --include='*.tsx'; then
  echo "ERROR: rolePermissions is still referenced."
  exit 1
fi

if grep -R "allowedKinds: \['client'\]\|allowedKinds: \[\"client\"\]" src --include='*.ts' --include='*.tsx'; then
  echo "ERROR: a staff-app route still permits client-only authentication."
  exit 1
fi

if grep -R "kind === 'client'\|kind === \"client\"" src --include='*.ts' --include='*.tsx'; then
  echo "ERROR: client-mode branching is still present."
  exit 1
fi

npm run format
npm run check
npm run test -- --run
npm run build:storybook

echo
echo "Portal parent route retired and foundation verification passed."
