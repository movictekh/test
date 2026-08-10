#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ! -f package.json ]] || ! grep -q '"name": "bomach_os_frontend-services"' package.json; then
  echo "ERROR: run this from bomach_os_frontend-services."
  exit 1
fi

echo "Repairing shared workspace-query compatibility without restoring it to Service Administration..."

python3 <<'PY'
from pathlib import Path

p = Path("src/modules/service-administration/api/service-administration.queries.ts")
s = p.read_text()

# Commercial/Fulfillment still consume this compatibility query.
if "import { serviceAdministrationApi } from './service-administration.api'\n" not in s:
    anchor = "import { serviceAdministrationBackendApi } from './service-administration.backend-api'\n"
    if anchor not in s:
        raise SystemExit("ERROR: backend-api import anchor not found")
    s = s.replace(
        anchor,
        "import { serviceAdministrationApi } from './service-administration.api'\n" + anchor,
        1,
    )

if "  workspace: () =>" not in s:
    anchor = "export const serviceAdministrationQueries = {\n"
    if anchor not in s:
        raise SystemExit("ERROR: queries object anchor not found")
    block = """export const serviceAdministrationQueries = {
  /**
   * Compatibility query for Commercial/Fulfillment while those modules still
   * consume the legacy Service workspace. Service Administration itself must
   * not use this query.
   */
  workspace: () =>
    queryOptions({
      queryKey: serviceAdministrationKeys.workspace(),
      queryFn: () => serviceAdministrationApi.getWorkspace(),
      staleTime: 30_000,
    }),

"""
    s = s.replace(anchor, block, 1)

p.write_text(s)
PY

npx prettier --write \
  src/modules/service-administration/api/service-administration.queries.ts

echo
echo "Boundary guards..."

if grep -n "serviceAdministrationQueries\.workspace()" \
  src/modules/service-administration/pages/ServiceAdministrationSectionPage.tsx >/dev/null 2>&1; then
  echo "ERROR: Service Administration page is using the mock workspace again."
  exit 1
fi

if ! grep -n "serviceAdministrationQueries\.workspace()" \
  src/modules/commercial/pages/CommercialSectionPage.tsx >/dev/null 2>&1; then
  echo "ERROR: expected Commercial compatibility consumer was not found."
  exit 1
fi

if ! grep -n "serviceAdministrationQueries\.workspace()" \
  src/modules/fulfillment/pages/FulfillmentSectionPage.tsx >/dev/null 2>&1; then
  echo "ERROR: expected Fulfillment compatibility consumer was not found."
  exit 1
fi

echo "Confirmed: Service Administration remains fully off the mock workspace."
echo "Confirmed: compatibility query exists only for downstream Commercial/Fulfillment consumers."

echo
echo "Typecheck..."
npm run typecheck

echo
echo "Focused Service Administration tests..."
npx vitest run \
  src/modules/service-administration/api/service-setup.orchestrator.test.ts \
  src/modules/service-administration/api/service-administration.live-mutations.test.ts \
  src/modules/service-administration/api/service-administration.queries.test.ts \
  src/modules/service-administration/mappers/service-catalogue.mapper.test.ts \
  src/modules/service-administration/mappers/pricing-config.pricing-types.test.ts \
  src/modules/service-administration/mappers/pricing-config.mapper.test.ts \
  src/modules/service-administration/permissions/service-administration.permissions.test.ts \
  src/modules/service-administration/screens/WorkflowDesignerScreen.test.tsx \
  src/modules/service-administration/screens/BranchActivationScreen.test.tsx

echo
echo "Lint changed production files..."
npx eslint \
  src/modules/service-administration/api/service-administration.queries.ts \
  src/modules/service-administration/types/service-administration.types.ts \
  src/modules/service-administration/mappers/service-catalogue.mapper.ts \
  src/modules/service-administration/pages/ServiceAdministrationSectionPage.tsx \
  src/modules/service-administration/workspaces/ServiceCatalogueWorkspaces.tsx \
  --max-warnings=0

echo
echo "SERVICE ADMINISTRATION FINAL COMPATIBILITY REPAIR COMPLETE"
