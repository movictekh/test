#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ! -f package.json ]] || ! grep -q '"name": "bomach_os_frontend-services"' package.json; then
  echo "ERROR: run this from bomach_os_frontend-services."
  exit 1
fi

echo "Pass 3 preflight..."
python3 <<'PY'
from pathlib import Path
import sys

required = [
    Path("src/modules/service-administration/components/ServiceAdministrationUi.tsx"),
    Path("src/shared/ui/index.ts"),
    Path("src/mocks"),
    Path("docs/ui-rebuild/README.md"),
]

missing = [str(p) for p in required if not p.exists()]
if missing:
    print("ERROR: missing required path(s): " + ", ".join(missing), file=sys.stderr)
    sys.exit(1)

service_ui = required[0].read_text(encoding="utf-8")
for name in [
    "CompactPageToolbar",
    "CompactActionButton",
    "SummaryStrip",
    "FilterBar",
    "FilterSelect",
]:
    if f"export function {name}" not in service_ui:
        print(f"ERROR: expected shared control {name} not found in ServiceAdministrationUi.tsx", file=sys.stderr)
        sys.exit(1)

mock_files = []
for p in Path("src").rglob("*.ts*"):
    if p.is_file() and "/ui-prototype/" in p.read_text(encoding="utf-8"):
        mock_files.append(p.as_posix())

print("Files using /ui-prototype/:")
for p in mock_files:
    print(" ", p)

if not mock_files:
    print("ERROR: no /ui-prototype/ transport paths found; repo differs from reviewed state.", file=sys.stderr)
    sys.exit(1)
PY

python3 <<'PY'
from pathlib import Path
import re
import subprocess

# ---------------------------------------------------------------------------
# A. Move generic module controls to shared/ui.
# ---------------------------------------------------------------------------
service_ui_path = Path(
    "src/modules/service-administration/components/ServiceAdministrationUi.tsx"
)
service_ui = service_ui_path.read_text(encoding="utf-8")

start_marker = "export function CompactPageToolbar("
end_marker = "export function StatusPill("

start = service_ui.find(start_marker)
end = service_ui.find(end_marker)

if start == -1 or end == -1 or end <= start:
    raise SystemExit(
        "ERROR: could not safely identify the generic control block in ServiceAdministrationUi.tsx"
    )

shared_block = service_ui[start:end].rstrip()

# The extracted block needs ReactNode + cn + IconSearch.
module_controls_dir = Path("src/shared/ui/module-controls")
module_controls_dir.mkdir(parents=True, exist_ok=True)
module_controls_path = module_controls_dir / "ModuleControls.tsx"
module_controls_index = module_controls_dir / "index.ts"

if module_controls_path.exists():
    raise SystemExit(
        "ERROR: shared module-controls already exists; refusing to overwrite."
    )

module_controls_path.write_text(
    """import { IconSearch } from '@tabler/icons-react'
import type { ReactNode } from 'react'

import { cn } from '@/shared/lib/cn'

"""
    + shared_block
    + "\n",
    encoding="utf-8",
)

module_controls_index.write_text(
    """export {
  CompactActionButton,
  CompactPageToolbar,
  FilterBar,
  FilterSelect,
  SummaryStrip,
} from './ModuleControls'
""",
    encoding="utf-8",
)

# Remove extracted generic definitions from the feature module.
service_ui = service_ui[:start] + service_ui[end:]

# Remove IconSearch from feature icon import if it is no longer used.
service_ui = service_ui.replace("  IconSearch,\n", "")

# Determine which shared controls are still used internally by the feature file.
shared_names = [
    "CompactActionButton",
    "CompactPageToolbar",
    "FilterBar",
    "FilterSelect",
    "SummaryStrip",
]
used_in_service_ui = [name for name in shared_names if re.search(rf"\b{name}\b", service_ui)]

if used_in_service_ui:
    import_block = (
        "import {\n  "
        + ",\n  ".join(used_in_service_ui)
        + ",\n} from '@/shared/ui/module-controls'\n"
    )
    anchor = "import { formatCurrency } from '@/shared/lib/formatters'\n"
    if anchor not in service_ui:
        raise SystemExit("ERROR: ServiceAdministrationUi import anchor not found.")
    service_ui = service_ui.replace(anchor, anchor + import_block, 1)

service_ui_path.write_text(service_ui, encoding="utf-8")

# Rewrite every import from ServiceAdministrationUi so generic controls come
# directly from shared/ui/module-controls.
old_source = "@/modules/service-administration/components/ServiceAdministrationUi"
pattern = re.compile(
    r"import\s*\{(?P<names>[^}]*)\}\s*from\s*['\"]"
    + re.escape(old_source)
    + r"['\"]\s*;?",
    re.MULTILINE,
)

for path in Path("src").rglob("*.ts*"):
    if not path.is_file() or path == service_ui_path:
        continue

    text = path.read_text(encoding="utf-8")
    if old_source not in text:
        continue

    def replace_import(match: re.Match[str]) -> str:
        raw_names = match.group("names")
        names = [part.strip() for part in raw_names.split(",") if part.strip()]
        shared = [name for name in names if name.split(" as ")[0].strip() in shared_names]
        feature = [name for name in names if name.split(" as ")[0].strip() not in shared_names]

        blocks = []
        if shared:
            blocks.append(
                "import {\n  "
                + ",\n  ".join(shared)
                + ",\n} from '@/shared/ui/module-controls'"
            )
        if feature:
            blocks.append(
                "import {\n  "
                + ",\n  ".join(feature)
                + ",\n} from '"
                + old_source
                + "'"
            )
        return "\n".join(blocks)

    updated = pattern.sub(replace_import, text)
    path.write_text(updated, encoding="utf-8")

# Export module controls from the shared UI barrel.
shared_index = Path("src/shared/ui/index.ts")
shared_text = shared_index.read_text(encoding="utf-8")
export_line = "export * from './module-controls'\n"
if export_line not in shared_text:
    shared_text += export_line
shared_index.write_text(shared_text, encoding="utf-8")

# ---------------------------------------------------------------------------
# B. Centralize and rename the development-only mock API transport prefix.
# ---------------------------------------------------------------------------
mock_api_path = Path("src/mocks/mock-api.ts")
if mock_api_path.exists():
    raise SystemExit("ERROR: src/mocks/mock-api.ts already exists; refusing to overwrite.")

mock_api_path.write_text(
    """/**
 * Development-only transport namespace used by MSW-backed feature adapters.
 *
 * Production backend endpoints must not use this prefix.
 */
export const MOCK_API_PREFIX = '/__mock-api__'
""",
    encoding="utf-8",
)

for path in Path("src").rglob("*.ts*"):
    if not path.is_file():
        continue

    text = path.read_text(encoding="utf-8")
    if "/ui-prototype/" not in text:
        continue

    updated = text.replace("/ui-prototype/", "${MOCK_API_PREFIX}/")

    # Convert simple quoted strings containing interpolation syntax into templates.
    updated = re.sub(
        r"'([^'\n]*\$\{MOCK_API_PREFIX\}[^'\n]*)'",
        lambda m: "`" + m.group(1) + "`",
        updated,
    )
    updated = re.sub(
        r'"([^"\n]*\$\{MOCK_API_PREFIX\}[^"\n]*)"',
        lambda m: "`" + m.group(1) + "`",
        updated,
    )

    import_line = "import { MOCK_API_PREFIX } from '@/mocks/mock-api'\n"
    if import_line not in updated:
        # Insert after the existing import block's first import statement.
        first_import_end = updated.find("\n", updated.find("import "))
        if first_import_end == -1:
            raise SystemExit(f"ERROR: import insertion point missing in {path}")
        updated = updated[: first_import_end + 1] + import_line + updated[first_import_end + 1 :]

    path.write_text(updated, encoding="utf-8")

# ---------------------------------------------------------------------------
# C. Clean remaining structural-development wording that belongs with this pass.
# ---------------------------------------------------------------------------
safe_replacements = {
    "/* Command Center — exact parity with Bomach_Service_Operations_OS_v1 dash() */":
        "/* Command Center */",
    "maps all prototype-aligned dashboard sections":
        "maps all dashboard sections",
    "Review these components against the prototype before business pages begin.":
        "Review the shared component states and interaction patterns.",
    "This demonstration shows the destructive confirmation pattern.":
        "This example shows the destructive confirmation pattern.",
    "abbreviates millions like the HTML prototype":
        "abbreviates million-scale values consistently",
    "uses the exact specialized services prototype labels":
        "uses the required specialized services labels",
    "clamps progress into the prototype range":
        "clamps progress into the supported range",
    "moves tasks through the exact prototype columns":
        "moves tasks through the configured workflow columns",
}

for path in Path("src").rglob("*"):
    if not path.is_file() or path.suffix not in {".ts", ".tsx", ".css"}:
        continue
    text = path.read_text(encoding="utf-8")
    updated = text
    for old, new in safe_replacements.items():
        updated = updated.replace(old, new)
    if updated != text:
        path.write_text(updated, encoding="utf-8")

# Clean comments in experience rules without changing the actual fixed values.
experience_rules = Path(
    "src/modules/experience-intelligence/workspaces/experience-intelligence.rules.ts"
)
if experience_rules.exists():
    text = experience_rules.read_text(encoding="utf-8")
    text = text.replace(
        "// The prototype exposes SLA as a branch KPI, but current mock contracts do",
        "// SLA is exposed as a branch KPI, but current mock contracts do",
    )
    text = text.replace(
        "// Exact prototype labels retained. These two measures need richer backend",
        "// These measures need richer backend",
    )
    experience_rules.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# D. Clarify docs ownership without moving historical files and breaking links.
# ---------------------------------------------------------------------------
ui_readme = Path("docs/ui-rebuild/README.md")
ui_readme.write_text(
    """# Bomach Service Operations — UI Engineering Reference

This directory preserves the design-rebuild strategy, fidelity rules, and implementation history used to establish the current Service Operations frontend.

## Current engineering guidance

Use these documents when maintaining or extending the existing frontend:

1. `03_Mock_API_and_Frontend_Contract_Standard.md`
2. `04_Pixel_Match_Review_Checklist.md`
3. `standards/CSS_Architecture_Standard.md`

The HTML reference remains useful for product language, information hierarchy, and workflow intent where no later product decision overrides it.

## Historical rebuild material

The following documents describe how the current UI was originally reconstructed and should be treated as implementation history rather than current runtime architecture:

- `01_Prototype_First_Strategy.md`
- `02_Four_Phase_UI_Roadmap.md`
- `05_Implementation_Log_Template.md`
- everything under `updates/`

Historical files remain in place for traceability and to avoid breaking relative documentation links. New engineering decisions should be documented as current architecture or standards rather than added as another rebuild phase.
""",
    encoding="utf-8",
)

updates_readme = Path("docs/ui-rebuild/updates/README.md")
if not updates_readme.exists():
    updates_readme.write_text(
        """# UI Rebuild Implementation History

This directory contains historical implementation records from the Service Operations UI reconstruction.

These files document past delivery phases, corrections, and sign-off decisions. They are retained for traceability and should not be treated as the authoritative source for current runtime architecture.

For current frontend guidance, use:

- `../README.md`
- `../03_Mock_API_and_Frontend_Contract_Standard.md`
- `../04_Pixel_Match_Review_Checklist.md`
- `../standards/CSS_Architecture_Standard.md`
""",
        encoding="utf-8",
    )
PY

echo
echo "Pass 3 structural guardrails..."

# Generic controls must no longer be defined in the Service Administration feature.
if rg -n \
  'export function (CompactPageToolbar|CompactActionButton|SummaryStrip|FilterBar|FilterSelect)' \
  src/modules/service-administration/components/ServiceAdministrationUi.tsx; then
  echo "ERROR: generic controls are still owned by Service Administration."
  exit 1
fi

# Cross-feature imports must not depend on Service Administration for those controls.
if rg -n \
  "from '@/modules/service-administration/components/ServiceAdministrationUi'" \
  src/modules/commercial src/modules/fulfillment src/modules/experience-intelligence src/modules/specialized-services src/modules/dashboard | \
  rg 'CompactPageToolbar|CompactActionButton|SummaryStrip|FilterBar|FilterSelect'; then
  echo "ERROR: a feature module still imports generic controls from Service Administration."
  exit 1
fi

if [[ ! -f src/shared/ui/module-controls/ModuleControls.tsx ]]; then
  echo "ERROR: shared module controls were not created."
  exit 1
fi

# Old mock namespace must be gone from runtime source.
if rg -n '/ui-prototype/' src; then
  echo "ERROR: /ui-prototype/ paths remain in src."
  exit 1
fi

if ! rg -q "MOCK_API_PREFIX = '/__mock-api__'" src/mocks/mock-api.ts; then
  echo "ERROR: centralized mock API prefix is missing."
  exit 1
fi

echo
echo "Remaining broad source hygiene matches (review only; legitimate mock/test terms may appear):"
rg -n -i \
  'prototype|demo|sign[ -]?off|parity|owning phase|literal translation|ui-[0-9]+\.[0-9]+' \
  src || true

echo
echo "Verification..."
npm run format
npm run check
npm run build:storybook

echo
echo "PASS 3 COMPLETE"
echo "Structural hardening applied:"
echo "  generic module controls moved to src/shared/ui/module-controls"
echo "  feature-to-feature UI dependency removed"
echo "  development mock API prefix centralized as /__mock-api__"
echo "  /ui-prototype/ runtime paths removed"
echo "  remaining structural development wording cleaned"
echo "  docs now distinguish current guidance from historical rebuild records"
echo
echo "No production backend endpoint contract was changed; the renamed namespace is MSW development transport only."
