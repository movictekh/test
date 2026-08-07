#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ! -f package.json ]] || ! grep -q '"name": "bomach_os_frontend-services"' package.json; then
  echo "ERROR: run this from bomach_os_frontend-services."
  exit 1
fi

echo "Pass 3 repair: inspecting the partially modified checkout..."

python3 <<'PY'
from pathlib import Path
import re
import sys

bad = []
pattern = re.compile(r"from\s+['\"][^'\"]+['\"]import\s+")

for path in Path("src").rglob("*.ts*"):
    if not path.is_file():
        continue
    text = path.read_text(encoding="utf-8")
    if pattern.search(text):
        bad.append(path.as_posix())

print("Malformed concatenated imports:")
for path in bad:
    print(" ", path)

expected = {
    "src/modules/commercial/pages/CommercialSectionPage.tsx",
    "src/modules/experience-intelligence/pages/ExperienceIntelligenceSectionPage.tsx",
    "src/modules/fulfillment/pages/FulfillmentSectionPage.tsx",
    "src/modules/specialized-services/pages/SpecializedServicesSectionPage.tsx",
}

unexpected = set(bad) - expected
if unexpected:
    print(
        "ERROR: unexpected malformed import files found: "
        + ", ".join(sorted(unexpected)),
        file=sys.stderr,
    )
    print("No files were changed.", file=sys.stderr)
    sys.exit(1)

if not bad:
    print("No malformed imports found. Continuing with Pass 3 verification.")
PY

python3 <<'PY'
from pathlib import Path
import re

pattern = re.compile(
    r"(from\s+['\"][^'\"]+['\"])(import\s+)"
)

for path in Path("src").rglob("*.ts*"):
    if not path.is_file():
        continue

    text = path.read_text(encoding="utf-8")
    updated = pattern.sub(r"\1\n\2", text)

    if updated != text:
        path.write_text(updated, encoding="utf-8")
        print(f"Fixed import boundary: {path}")
PY

echo
echo "Syntax guardrail..."

if rg -n "from ['\"][^'\"]+['\"]import " src; then
  echo "ERROR: concatenated imports remain."
  exit 1
fi

echo
echo "Checking Pass 3 structural results..."

if [[ ! -f src/shared/ui/module-controls/ModuleControls.tsx ]]; then
  echo "ERROR: shared module controls are missing."
  exit 1
fi

if [[ ! -f src/mocks/mock-api.ts ]]; then
  echo "ERROR: centralized mock API config is missing."
  exit 1
fi

if rg -n '/ui-prototype/' src; then
  echo "ERROR: old /ui-prototype/ namespace remains."
  exit 1
fi

if ! rg -q "MOCK_API_PREFIX = '/__mock-api__'" src/mocks/mock-api.ts; then
  echo "ERROR: /__mock-api__ prefix is not configured correctly."
  exit 1
fi

if rg -n \
  'export function (CompactPageToolbar|CompactActionButton|SummaryStrip|FilterBar|FilterSelect)' \
  src/modules/service-administration/components/ServiceAdministrationUi.tsx; then
  echo "ERROR: generic controls are still defined under Service Administration."
  exit 1
fi

echo
echo "Checking shared-control imports..."
rg -n "shared/ui/module-controls" \
  src/modules/commercial \
  src/modules/fulfillment \
  src/modules/experience-intelligence \
  src/modules/specialized-services \
  src/modules/service-administration || true

# Service Administration page used a relative import; Pass 3 only rewrote the
# absolute @/modules/... path. Align it with the shared controls barrel.
python3 <<'PY'
from pathlib import Path

path = Path("src/modules/service-administration/pages/ServiceAdministrationSectionPage.tsx")
text = path.read_text(encoding="utf-8")
old = "import { CompactPageToolbar, CompactActionButton } from '../components/ServiceAdministrationUi'\n"
new = "import { CompactPageToolbar, CompactActionButton } from '@/shared/ui/module-controls'\n"
if old in text:
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("Fixed Service Administration shared-control import.")
elif "from '@/shared/ui/module-controls'" in text and "CompactPageToolbar" in text:
    print("Service Administration shared-control import already correct.")
else:
    raise SystemExit("ERROR: Service Administration page is missing CompactPageToolbar import.")
PY

echo
echo "Formatting..."
npm run format

echo
echo "Full repository verification..."
npm run check
npm run build:storybook

echo
echo "PASS 3 REPAIR COMPLETE"
echo "The partially applied structural hardening has been repaired and verified."
echo
echo "Current architecture:"
echo "  Shared module controls -> src/shared/ui/module-controls"
echo "  Dev mock transport     -> /__mock-api__ via src/mocks/mock-api.ts"
echo "  Historical UI docs     -> explicitly separated from current guidance"
