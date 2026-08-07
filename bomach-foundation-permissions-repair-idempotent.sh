#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ! -f package.json ]] || ! grep -q '"name": "bomach_os_frontend-services"' package.json; then
  echo "Error: run this from bomach_os_frontend-services."
  exit 1
fi

python3 <<'PY'
from pathlib import Path

def read(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text()

def write(path: str, content: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(content)

# ---------------------------------------------------------------------------
# 1. Permissions: backend is sole authorization source.
# ---------------------------------------------------------------------------
write(
    "src/app/permissions/permissions.ts",
    """import type { AuthUser } from '@/app/auth'

import type { AppPermission, PermissionMode } from './permission.types'

export const PERMISSIONS = {
  dashboardRead: 'dashboard.read',
  serviceRead: 'service.read',
  serviceCreate: 'service.create',
  serviceUpdate: 'service.update',
  requestRead: 'request.read',
  requestCreate: 'request.create',
  requestUpdate: 'request.update',
  quoteRead: 'quote.read',
  quoteCreate: 'quote.create',
  quoteApprove: 'quote.approve',
  invoiceRead: 'invoice.read',
  invoiceCreate: 'invoice.create',
  paymentConfirm: 'payment.confirm',
  approvalRead: 'approval.read',
  approvalAct: 'approval.act',
  orderRead: 'order.read',
  orderUpdate: 'order.update',
  taskRead: 'task.read',
  taskUpdate: 'task.update',
  deliverableRead: 'deliverable.read',
  deliverableUpdate: 'deliverable.update',
  deliverableApprove: 'deliverable.approve',
  realEstateRead: 'real-estate.read',
  reportRead: 'report.read',
  auditRead: 'audit.read',
} as const satisfies Record<string, AppPermission>

export function getUserPermissions(user: AuthUser | null): readonly AppPermission[] {
  return user?.permissions ?? []
}

export function hasPermission(user: AuthUser | null, permission: AppPermission): boolean {
  return getUserPermissions(user).includes(permission)
}

export function hasPermissions(
  user: AuthUser | null,
  permissions: readonly AppPermission[],
  mode: PermissionMode = 'all',
): boolean {
  if (permissions.length === 0) return true

  const granted = new Set(getUserPermissions(user))

  return mode === 'all'
    ? permissions.every((permission) => granted.has(permission))
    : permissions.some((permission) => granted.has(permission))
}
""",
)

p = "src/app/permissions/permission.types.ts"
text = read(p).replace("  'portal.read',\n", "")
write(p, text)

p = "src/app/permissions/index.ts"
text = read(p).replace("  rolePermissions,\n", "")
write(p, text)

# ---------------------------------------------------------------------------
# 2. Staff-only auth model.
# ---------------------------------------------------------------------------
p = "src/app/auth/auth.types.ts"
text = read(p)
text = text.replace("  'CLIENT',\n", "")
if "  'UNKNOWN',\n" not in text:
    text = text.replace("  'PROJECT_MANAGER',\n", "  'PROJECT_MANAGER',\n  'UNKNOWN',\n")
text = text.replace(
    "export const AUTH_USER_KINDS = ['staff', 'client'] as const",
    "export const AUTH_USER_KINDS = ['staff'] as const",
)
write(p, text)

write(
    "src/modules/auth/mappers/auth.mapper.ts",
    """import { APP_PERMISSION_VALUES, type AppPermission } from '@/app/permissions/permission.types'
import type { AppRole } from '@/app/auth/auth.types'

import type { RoleResponseDto, UserResponseDto } from '../types/auth.contracts'
import type { AuthenticatedUser } from '../types/auth.types'

const knownPermissions = new Set<string>(APP_PERMISSION_VALUES)

function normaliseRoleName(value: string): AppRole {
  const normalized = value
    .trim()
    .toUpperCase()
    .replace(/[\\s/-]+/g, '_')

  const aliases: Record<string, AppRole> = {
    CEO_FOUNDER: 'CEO',
    CEO: 'CEO',
    SERVICE_ADMINISTRATOR: 'SERVICE_ADMINISTRATOR',
    HEAD_OF_OPERATIONS: 'HEAD_OF_OPERATIONS',
    SERVICE_MANAGER: 'SERVICE_MANAGER',
    FINANCE: 'FINANCE',
    FINANCE_AND_ACCOUNTS: 'FINANCE',
    SALES_CSRC: 'SALES_CSRC',
    SALES_CSR: 'SALES_CSRC',
    CIVIL_ENGINEER: 'CIVIL_ENGINEER',
    LAND_SURVEYOR: 'LAND_SURVEYOR',
    PROPERTY_MANAGER: 'PROPERTY_MANAGER',
    PROJECT_MANAGER: 'PROJECT_MANAGER',
  }

  return aliases[normalized] ?? 'UNKNOWN'
}

function flattenPermissions(permissions: Record<string, string[]>): string[] {
  return Object.entries(permissions).flatMap(([resource, actions]) =>
    actions.map((action) => `${resource}.${action}`),
  )
}

function getInitials(firstName: string | null, lastName: string | null, username: string): string {
  const initials = [firstName, lastName]
    .filter((value): value is string => Boolean(value?.trim()))
    .map((value) => value.trim().charAt(0).toUpperCase())
    .join('')

  return initials || username.slice(0, 2).toUpperCase()
}

export function mapAuthenticatedUser(
  user: UserResponseDto,
  role: RoleResponseDto,
): AuthenticatedUser {
  const backendPermissions = flattenPermissions(role.permissions)
  const permissions = backendPermissions.filter((permission): permission is AppPermission =>
    knownPermissions.has(permission),
  )

  const firstName = user.first_name?.trim() || ''
  const lastName = user.last_name?.trim() || ''
  const name = [firstName, lastName].filter(Boolean).join(' ') || user.username

  return {
    id: String(user.id),
    name,
    email: user.email,
    username: user.username,
    initials: getInitials(user.first_name, user.last_name, user.username),
    role: normaliseRoleName(role.name),
    roleLabel: role.name || 'Staff User',
    kind: 'staff',
    permissions,
    backendPermissions,
    isVerified: user.is_verified,
  }
}
""",
)

p = "src/modules/auth/api/auth.api.ts"
text = read(p)

# Only replace old detector when still present.
if "async function detectUserContext" in text:
    start = text.index("async function detectUserContext")
    end = text.index("\nasync function login", start)
    text = (
        text[:start]
        + """async function loadStaffUser(user: UserResponseDto): Promise<AuthenticatedUser> {
  const role = await apiClient.get<RoleResponseDto>(`/roles/employees/${user.id}`)
  return mapAuthenticatedUser(user, role)
}
"""
        + text[end:]
    )

# Ensure the new loader exists even on odd partial states.
if "async function loadStaffUser" not in text:
    marker = "async function login"
    idx = text.index(marker)
    text = (
        text[:idx]
        + """async function loadStaffUser(user: UserResponseDto): Promise<AuthenticatedUser> {
  const role = await apiClient.get<RoleResponseDto>(`/roles/employees/${user.id}`)
  return mapAuthenticatedUser(user, role)
}

"""
        + text[idx:]
    )

text = text.replace("return await detectUserContext(user)", "return await loadStaffUser(user)")
text = text.replace("return mapAuthenticatedUser(user, role, 'staff')", "return mapAuthenticatedUser(user, role)")
write(p, text)

# ---------------------------------------------------------------------------
# 3. Remove portal navigation.
# ---------------------------------------------------------------------------
p = "src/app/navigation/navigation.config.ts"
text = read(p)
text = text.replace("const portalShellRoute = '/portal/shell/$section' as NavigationPath\n", "")
portal_start = text.find("\nexport const clientPortalNavigation = [")
if portal_start >= 0:
    text = text[:portal_start].rstrip() + "\n"
write(p, text)

p = "src/app/navigation/index.ts"
text = read(p).replace(
    "export { clientPortalNavigation, operationsNavigation } from './navigation.config'",
    "export { operationsNavigation } from './navigation.config'",
)
write(p, text)

# ---------------------------------------------------------------------------
# 4. Remove ClientPortalLayout entirely and remove references to it.
# ---------------------------------------------------------------------------
layout = Path("src/app/layouts/ClientPortalLayout.tsx")
if layout.exists():
    layout.unlink()

# Update layout barrel exports if present.
for barrel in [
    "src/app/layouts/index.ts",
    "src/app/layouts/layouts.ts",
]:
    p = Path(barrel)
    if not p.exists():
        continue
    text = p.read_text()
    lines = [
        line
        for line in text.splitlines()
        if "ClientPortalLayout" not in line
    ]
    p.write_text("\n".join(lines).rstrip() + "\n")

# Remove imports/usages from route/root files if any.
for p in Path("src").rglob("*.tsx"):
    text = p.read_text()
    if "ClientPortalLayout" not in text:
        continue

    text = text.replace(
        "import { ClientPortalLayout } from '@/app/layouts/ClientPortalLayout'\n",
        "",
    )
    text = text.replace(
        "import { ClientPortalLayout } from '@/app/layouts'\n",
        "",
    )
    # If a portal route wrapped content with the layout, those route files are
    # retired below, so leave no active staff-app dependency.
    p.write_text(text)

# ---------------------------------------------------------------------------
# 5. Remove portal buttons from staff screens, idempotently.
# ---------------------------------------------------------------------------
replacements = {
    "src/modules/service-administration/pages/ServiceAdministrationSectionPage.tsx": [
        (
            "import { IconFilePlus, IconPlus, IconUserScreen } from '@tabler/icons-react'",
            "import { IconFilePlus, IconPlus } from '@tabler/icons-react'",
        ),
        (
"""            <PrototypeButton
              onClick={() =>
                void navigate({
                  to: '/portal/dashboard',
                })
              }
            >
              <IconUserScreen size={14} />
              Client Portal
            </PrototypeButton>
""",
            "",
        ),
    ],
    "src/modules/commercial/pages/CommercialSectionPage.tsx": [
        (
            "import { IconFilePlus, IconPlus, IconUserScreen } from '@tabler/icons-react'",
            "import { IconFilePlus, IconPlus } from '@tabler/icons-react'",
        ),
        (
"""        secondaryAction={
          <PrototypeButton onClick={() => void navigate({ to: '/portal/dashboard' })}>
            <IconUserScreen size={14} />
            Client Portal
          </PrototypeButton>
        }
""",
            "",
        ),
    ],
    "src/modules/fulfillment/pages/FulfillmentSectionPage.tsx": [
        (
            "import { IconFilePlus, IconPlus, IconUserScreen } from '@tabler/icons-react'",
            "import { IconFilePlus, IconPlus } from '@tabler/icons-react'",
        ),
        (
            "import { useNavigate } from '@tanstack/react-router'\n",
            "",
        ),
        (
            "  const navigate = useNavigate()\n",
            "",
        ),
        (
"""        secondaryAction={
          <PrototypeButton onClick={() => void navigate({ to: '/portal/dashboard' })}>
            <IconUserScreen size={14} />
            Client Portal
          </PrototypeButton>
        }
""",
            "",
        ),
    ],
}

for path, pairs in replacements.items():
    text = read(path)
    for old, new in pairs:
        text = text.replace(old, new)
    write(path, text)

# Specialized Services also had a Client Portal toolbar action in the Stage 3 implementation.
p = "src/modules/specialized-services/pages/SpecializedServicesSectionPage.tsx"
if Path(p).exists():
    text = read(p)
    text = text.replace(
        "import { IconUserScreen } from '@tabler/icons-react'\n",
        "",
    )
    text = text.replace(
        "import { useNavigate } from '@tanstack/react-router'\n",
        "import { useNavigate } from '@tanstack/react-router'\n",
    )
    block = """        secondaryAction={
          <PrototypeButton onClick={() => void navigate({ to: '/portal/dashboard' })}>
            <IconUserScreen size={14} />
            Client Portal
          </PrototypeButton>
        }
"""
    text = text.replace(block, "")
    write(p, text)

# ---------------------------------------------------------------------------
# 6. Retire old portal routes.
# ---------------------------------------------------------------------------
routes = {
    "src/routes/portal/dashboard.tsx": "/portal/dashboard",
    "src/routes/portal/shell/$section.tsx": "/portal/shell/$section",
}

for path, route in routes.items():
    if Path(path).exists():
        write(
            path,
            f"""import {{ createFileRoute, redirect }} from '@tanstack/react-router'

export const Route = createFileRoute('{route}')({{
  beforeLoad: () => {{
    return redirect({{
      to: '/app/dashboard',
      replace: true,
    }})
  }},
  component: () => null,
}})
""",
        )

foundation_page = Path("src/modules/foundation/pages/ClientPortalFoundationPage.tsx")
if foundation_page.exists():
    foundation_page.unlink()

# ---------------------------------------------------------------------------
# 7. Tests.
# ---------------------------------------------------------------------------
write(
    "src/app/permissions/permissions.test.ts",
    """import { describe, expect, it } from 'vitest'

import type { AuthUser } from '@/app/auth'

import { PERMISSIONS, hasPermission, hasPermissions } from './permissions'

function makeUser(
  permissions: AuthUser['permissions'],
  role: AuthUser['role'] = 'SERVICE_ADMINISTRATOR',
): AuthUser {
  return {
    id: 'staff-1',
    name: 'Staff User',
    email: 'staff@bomach.local',
    username: 'staff',
    initials: 'SU',
    role,
    roleLabel: role,
    kind: 'staff',
    permissions,
    backendPermissions: [...permissions],
    isVerified: true,
  }
}

describe('permission helpers', () => {
  it('treats an empty backend permission payload as zero access', () => {
    const user = makeUser([])

    expect(hasPermission(user, PERMISSIONS.dashboardRead)).toBe(false)
    expect(hasPermission(user, PERMISSIONS.serviceCreate)).toBe(false)
    expect(hasPermission(user, PERMISSIONS.realEstateRead)).toBe(false)
  })

  it('does not grant access from a frontend role name', () => {
    expect(
      hasPermission(makeUser([], 'SERVICE_ADMINISTRATOR'), PERMISSIONS.serviceCreate),
    ).toBe(false)

    expect(
      hasPermission(makeUser([], 'HEAD_OF_OPERATIONS'), PERMISSIONS.orderUpdate),
    ).toBe(false)
  })

  it('grants only explicit backend-provided permissions', () => {
    const user = makeUser([
      PERMISSIONS.dashboardRead,
      PERMISSIONS.orderRead,
      PERMISSIONS.taskRead,
    ])

    expect(hasPermission(user, PERMISSIONS.dashboardRead)).toBe(true)
    expect(hasPermission(user, PERMISSIONS.orderRead)).toBe(true)
    expect(hasPermission(user, PERMISSIONS.taskRead)).toBe(true)
    expect(hasPermission(user, PERMISSIONS.orderUpdate)).toBe(false)
    expect(hasPermission(user, PERMISSIONS.realEstateRead)).toBe(false)
  })

  it('supports any-permission checks using only the backend permission set', () => {
    const user = makeUser([PERMISSIONS.requestRead])

    expect(
      hasPermissions(
        user,
        [PERMISSIONS.paymentConfirm, PERMISSIONS.requestRead],
        'any',
      ),
    ).toBe(true)
  })
})
""",
)

write(
    "src/modules/auth/mappers/auth.mapper.test.ts",
    """import { describe, expect, it } from 'vitest'

import { PERMISSIONS } from '@/app/permissions'

import type { RoleResponseDto, UserResponseDto } from '../types/auth.contracts'
import { mapAuthenticatedUser } from './auth.mapper'

const user: UserResponseDto = {
  id: 7,
  email: 'staff@bomach.local',
  username: 'staff.user',
  first_name: 'Staff',
  last_name: 'User',
  phone_number: null,
  is_verified: true,
  created_at: '2026-08-07T00:00:00Z',
}

function role(
  name: string,
  permissions: RoleResponseDto['permissions'],
): RoleResponseDto {
  return {
    id: 1,
    name,
    branches: [],
    permissions,
    created_at: '2026-08-07T00:00:00Z',
    updated_at: '2026-08-07T00:00:00Z',
  }
}

describe('mapAuthenticatedUser', () => {
  it('maps an empty backend permission payload to zero frontend permissions', () => {
    const mapped = mapAuthenticatedUser(
      user,
      role('Service Administrator', {}),
    )

    expect(mapped.permissions).toEqual([])
  })

  it('maps only supported backend capabilities', () => {
    const mapped = mapAuthenticatedUser(
      user,
      role('Service Manager', {
        order: ['read', 'update'],
        task: ['read'],
        unsupported_resource: ['read'],
      }),
    )

    expect(mapped.permissions).toEqual([
      PERMISSIONS.orderRead,
      PERMISSIONS.orderUpdate,
      PERMISSIONS.taskRead,
    ])

    expect(mapped.backendPermissions).toContain('unsupported_resource.read')
  })

  it('does not convert an unknown backend role into a privileged frontend role', () => {
    const mapped = mapAuthenticatedUser(
      user,
      role('Regional Operations Supervisor', {
        order: ['read'],
      }),
    )

    expect(mapped.role).toBe('UNKNOWN')
    expect(mapped.roleLabel).toBe('Regional Operations Supervisor')
    expect(mapped.permissions).toEqual([PERMISSIONS.orderRead])
  })
})
""",
)

# Navigation test: role tables must not be asserted anymore.
p = Path("src/app/navigation/navigation.config.test.ts")
if p.exists():
    text = p.read_text()
    text = text.replace(
        "import { PERMISSIONS, rolePermissions } from '@/app/permissions'",
        "import { PERMISSIONS } from '@/app/permissions'",
    )
    old = """  it('exposes real estate inventory to operational management roles', () => {
    expect(rolePermissions.SERVICE_ADMINISTRATOR).toContain(PERMISSIONS.realEstateRead)
    expect(rolePermissions.HEAD_OF_OPERATIONS).toContain(PERMISSIONS.realEstateRead)
    expect(rolePermissions.SERVICE_MANAGER).toContain(PERMISSIONS.realEstateRead)
  })
"""
    new = """  it('declares backend capability requirements without assigning them to roles', () => {
    const group = operationsNavigation.find(
      (item) => item.id === 'specialized-services',
    )

    const realEstate = group?.items.find(
      (item) => item.id === 'real-estate-inventory',
    )

    const surveyEngineering = group?.items.find(
      (item) => item.id === 'survey-engineering-others',
    )

    expect(realEstate?.permissions).toEqual([PERMISSIONS.realEstateRead])
    expect(surveyEngineering?.permissions).toEqual([PERMISSIONS.orderRead])
  })
"""
    text = text.replace(old, new)
    p.write_text(text)

write(
    "docs/ui-rebuild/updates/FOUNDATION_BACKEND_PERMISSIONS_AND_PORTAL_BOUNDARY.md",
    """# Foundation correction — backend permissions and Client Portal boundary

`bomach_os_frontend-services` is the internal staff Service Operations application.
The Client Portal is a separate application and is no longer owned here.

## Authorization

```text
/auth/me
→ /roles/employees/{employee_id}
→ role.permissions
→ AuthUser.permissions
→ navigation / route / action guards
```

Frontend `PERMISSIONS` constants declare the capabilities required by features.
They do not assign capabilities to roles.

An empty backend permission payload therefore means zero frontend access.
Unknown backend role names normalize to the non-authorizing `UNKNOWN` marker
while the backend role label remains visible.

Legacy `/portal/*` routes redirect to `/app/dashboard`.

Frontend guards are UX safeguards only; backend endpoints remain the real
security boundary and must independently enforce authorization.
""",
)

PY

echo "Checking for stale frontend authorization or portal ownership..."

if grep -R "rolePermissions" src --include='*.ts' --include='*.tsx'; then
  echo "ERROR: rolePermissions is still referenced."
  exit 1
fi

if grep -R "portalRead" src --include='*.ts' --include='*.tsx'; then
  echo "ERROR: portalRead is still referenced."
  exit 1
fi

if grep -R "clientPortalNavigation" src --include='*.ts' --include='*.tsx'; then
  echo "ERROR: clientPortalNavigation is still referenced."
  exit 1
fi

if grep -R "ClientPortalLayout" src --include='*.ts' --include='*.tsx'; then
  echo "ERROR: ClientPortalLayout is still referenced."
  exit 1
fi

if grep -R "kind === 'client'\|kind === \"client\"" src --include='*.ts' --include='*.tsx'; then
  echo "ERROR: client-mode authorization branching is still present."
  exit 1
fi

npm run format
npm run check
npm run test -- --run
npm run build:storybook

echo
echo "Foundation correction complete."
