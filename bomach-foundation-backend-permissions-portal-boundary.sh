#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ! -f package.json ]] || ! grep -q '"name": "bomach_os_frontend-services"' package.json; then
  echo "Run this from bomach_os_frontend-services."
  exit 1
fi

python3 <<'PY'
from pathlib import Path


def r(path: str) -> str:
    return Path(path).read_text()


def w(path: str, text: str) -> None:
    Path(path).write_text(text)

# 1) Backend permissions are authoritative.
w(
    'src/app/permissions/permissions.ts',
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

p = 'src/app/permissions/permission.types.ts'
t = r(p).replace("  'portal.read',\n", '')
w(p, t)

p = 'src/app/permissions/index.ts'
t = r(p).replace('  rolePermissions,\n', '')
w(p, t)

# 2) Staff-only auth; roles are display metadata only.
p = 'src/app/auth/auth.types.ts'
t = r(p).replace("  'CLIENT',\n", '')
if "  'UNKNOWN',\n" not in t:
    t = t.replace("  'PROJECT_MANAGER',\n", "  'PROJECT_MANAGER',\n  'UNKNOWN',\n")
t = t.replace(
    "export const AUTH_USER_KINDS = ['staff', 'client'] as const",
    "export const AUTH_USER_KINDS = ['staff'] as const",
)
w(p, t)

w(
    'src/modules/auth/mappers/auth.mapper.ts',
    """import { APP_PERMISSION_VALUES, type AppPermission } from '@/app/permissions/permission.types'
import type { AppRole } from '@/app/auth/auth.types'

import type { RoleResponseDto, UserResponseDto } from '../types/auth.contracts'
import type { AuthenticatedUser } from '../types/auth.types'

const knownPermissions = new Set<string>(APP_PERMISSION_VALUES)

function normaliseRoleName(value: string): AppRole {
  const normalized = value.trim().toUpperCase().replace(/[\\s/-]+/g, '_')

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

p = 'src/modules/auth/api/auth.api.ts'
t = r(p)
start = t.find('async function detectUserContext')
end = t.find('\nasync function login', start)
if start < 0 or end < 0:
    raise SystemExit('detectUserContext not found in auth.api.ts')
replacement = """async function loadStaffUser(user: UserResponseDto): Promise<AuthenticatedUser> {
  const role = await apiClient.get<RoleResponseDto>(`/roles/employees/${user.id}`)
  return mapAuthenticatedUser(user, role)
}
"""
t = t[:start] + replacement + t[end:]
t = t.replace('    return await detectUserContext(user)', '    return await loadStaffUser(user)')
w(p, t)

# 3) Remove Client Portal navigation ownership.
p = 'src/app/navigation/navigation.config.ts'
t = r(p).replace("const portalShellRoute = '/portal/shell/$section' as NavigationPath\n", '')
portal_start = t.find('\nexport const clientPortalNavigation = [')
if portal_start >= 0:
    t = t[:portal_start].rstrip() + '\n'
w(p, t)

p = 'src/app/navigation/index.ts'
t = r(p).replace(
    "export { clientPortalNavigation, operationsNavigation } from './navigation.config'",
    "export { operationsNavigation } from './navigation.config'",
)
w(p, t)

# 4) Remove Client Portal buttons from staff pages.
p = 'src/modules/service-administration/pages/ServiceAdministrationSectionPage.tsx'
t = r(p).replace(
    "import { IconFilePlus, IconPlus, IconUserScreen } from '@tabler/icons-react'",
    "import { IconFilePlus, IconPlus } from '@tabler/icons-react'",
)
block = """            <PrototypeButton
              onClick={() =>
                void navigate({
                  to: '/portal/dashboard',
                })
              }
            >
              <IconUserScreen size={14} />
              Client Portal
            </PrototypeButton>
"""
if block not in t:
    raise SystemExit('Service Administration Client Portal button not found')
w(p, t.replace(block, '', 1))

p = 'src/modules/commercial/pages/CommercialSectionPage.tsx'
t = r(p).replace(
    "import { IconFilePlus, IconPlus, IconUserScreen } from '@tabler/icons-react'",
    "import { IconFilePlus, IconPlus } from '@tabler/icons-react'",
)
block = """        secondaryAction={
          <PrototypeButton onClick={() => void navigate({ to: '/portal/dashboard' })}>
            <IconUserScreen size={14} />
            Client Portal
          </PrototypeButton>
        }
"""
if block not in t:
    raise SystemExit('Commercial Client Portal action not found')
w(p, t.replace(block, '', 1))

p = 'src/modules/fulfillment/pages/FulfillmentSectionPage.tsx'
t = r(p).replace(
    "import { IconFilePlus, IconPlus, IconUserScreen } from '@tabler/icons-react'",
    "import { IconFilePlus, IconPlus } from '@tabler/icons-react'",
)
t = t.replace("import { useNavigate } from '@tanstack/react-router'\n", '')
t = t.replace('  const navigate = useNavigate()\n', '')
block = """        secondaryAction={
          <PrototypeButton onClick={() => void navigate({ to: '/portal/dashboard' })}>
            <IconUserScreen size={14} />
            Client Portal
          </PrototypeButton>
        }
"""
if block not in t:
    raise SystemExit('Fulfillment Client Portal action not found')
w(p, t.replace(block, '', 1))

# 5) Retire legacy internal portal routes without breaking generated route imports.
for path, route in [
    ('src/routes/portal/dashboard.tsx', '/portal/dashboard'),
    ('src/routes/portal/shell/$section.tsx', '/portal/shell/$section'),
]:
    if Path(path).exists():
        w(
            path,
            f"""import {{ createFileRoute, redirect }} from '@tanstack/react-router'

export const Route = createFileRoute('{route}')({{
  beforeLoad: () => {{
    return redirect({{ to: '/app/dashboard', replace: true }})
  }},
  component: () => null,
}})
""",
        )

foundation = Path('src/modules/foundation/pages/ClientPortalFoundationPage.tsx')
if foundation.exists():
    foundation.unlink()

# 6) Permission regression tests.
w(
    'src/app/permissions/permissions.test.ts',
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
    expect(hasPermission(makeUser([], 'SERVICE_ADMINISTRATOR'), PERMISSIONS.serviceCreate)).toBe(false)
    expect(hasPermission(makeUser([], 'HEAD_OF_OPERATIONS'), PERMISSIONS.orderUpdate)).toBe(false)
  })

  it('grants only explicit backend-provided permissions', () => {
    const user = makeUser([PERMISSIONS.dashboardRead, PERMISSIONS.orderRead, PERMISSIONS.taskRead])
    expect(hasPermission(user, PERMISSIONS.orderRead)).toBe(true)
    expect(hasPermission(user, PERMISSIONS.orderUpdate)).toBe(false)
    expect(hasPermission(user, PERMISSIONS.realEstateRead)).toBe(false)
  })

  it('supports any-permission checks using the backend permission set', () => {
    const user = makeUser([PERMISSIONS.requestRead])
    expect(hasPermissions(user, [PERMISSIONS.paymentConfirm, PERMISSIONS.requestRead], 'any')).toBe(true)
  })
})
""",
)

w(
    'src/modules/auth/mappers/auth.mapper.test.ts',
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

function role(name: string, permissions: RoleResponseDto['permissions']): RoleResponseDto {
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
    expect(mapAuthenticatedUser(user, role('Service Administrator', {})).permissions).toEqual([])
  })

  it('maps only recognized backend permissions', () => {
    const mapped = mapAuthenticatedUser(user, role('Service Manager', {
      order: ['read', 'update'],
      task: ['read'],
      unsupported_resource: ['read'],
    }))
    expect(mapped.permissions).toEqual([
      PERMISSIONS.orderRead,
      PERMISSIONS.orderUpdate,
      PERMISSIONS.taskRead,
    ])
    expect(mapped.backendPermissions).toContain('unsupported_resource.read')
  })

  it('does not convert an unknown backend role into a privileged frontend role', () => {
    const mapped = mapAuthenticatedUser(user, role('Regional Operations Supervisor', {
      order: ['read'],
    }))
    expect(mapped.role).toBe('UNKNOWN')
    expect(mapped.roleLabel).toBe('Regional Operations Supervisor')
    expect(mapped.permissions).toEqual([PERMISSIONS.orderRead])
  })
})
""",
)

p = Path('src/app/navigation/navigation.config.test.ts')
if p.exists():
    t = p.read_text().replace(
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
    const group = operationsNavigation.find((item) => item.id === 'specialized-services')
    const realEstate = group?.items.find((item) => item.id === 'real-estate-inventory')
    const surveyEngineering = group?.items.find((item) => item.id === 'survey-engineering-others')

    expect(realEstate?.permissions).toEqual([PERMISSIONS.realEstateRead])
    expect(surveyEngineering?.permissions).toEqual([PERMISSIONS.orderRead])
  })
"""
    if old not in t:
        raise SystemExit('Navigation role-permission test not found')
    p.write_text(t.replace(old, new))

Path('docs/ui-rebuild/updates/FOUNDATION_BACKEND_PERMISSIONS_AND_PORTAL_BOUNDARY.md').write_text(
    """# Foundation correction — backend permissions and Client Portal boundary

`bomach_os_frontend-services` is the internal staff Service Operations application.
The Client Portal is a separate application.

```text
/auth/me
→ /roles/employees/{employee_id}
→ role.permissions
→ AuthUser.permissions
→ navigation / route / action guards
```

Frontend permission constants declare feature requirements only. They never assign
permissions to roles. Empty backend permissions mean zero access. Unknown backend
role names are display metadata and normalize to `UNKNOWN`; they do not inherit
another role's permissions.

Legacy `/portal/*` routes redirect to `/app/dashboard`. Backend endpoints remain
the authoritative security boundary and must enforce permissions independently.
"""
)
PY

# Guardrails: the staff app must fail closed.
if grep -R "rolePermissions" src --include='*.ts' --include='*.tsx'; then
  echo "rolePermissions is still referenced"
  exit 1
fi
if grep -R "portalRead" src --include='*.ts' --include='*.tsx'; then
  echo "portalRead is still referenced"
  exit 1
fi
if grep -R "clientPortalNavigation" src --include='*.ts' --include='*.tsx'; then
  echo "clientPortalNavigation is still referenced"
  exit 1
fi
if grep -R "kind === 'client'\|kind === \"client\"" src --include='*.ts' --include='*.tsx'; then
  echo "client-mode branching is still present"
  exit 1
fi

npm run format
npm run check
npm run test -- --run
npm run build:storybook

echo "Foundation correction complete."
