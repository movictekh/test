import { APP_PERMISSION_VALUES, PERMISSIONS, type AppPermission } from '@/app/permissions'

const canonicalAppPermissions = new Set<string>(APP_PERMISSION_VALUES)

/**
 * Verified against the live auth/role API catalog generated 2026-08-07.
 *
 * Do not add inferred aliases here. Extend this table only when a backend
 * module contract or live role payload proves the resource/action pair.
 */
const VERIFIED_BACKEND_PERMISSION_MAP: Readonly<Record<string, AppPermission>> = {
  'orders.view': PERMISSIONS.orderRead,
  'orders.list': PERMISSIONS.orderRead,
  'service_requests.view': PERMISSIONS.requestRead,
  'service_requests.list': PERMISSIONS.requestRead,
  'service_requests.create': PERMISSIONS.requestCreate,
}

export interface BackendPermissionMapping {
  permissions: AppPermission[]
  backendPermissions: string[]
  unmappedBackendPermissions: string[]
}

function normalize(value: string): string {
  return value.trim().toLowerCase()
}

export function flattenBackendPermissions(permissions: Record<string, string[]>): string[] {
  return Object.entries(permissions).flatMap(([resource, actions]) => {
    const normalizedResource = normalize(resource)
    return actions.map((action) => `${normalizedResource}.${normalize(action)}`)
  })
}

export function mapBackendPermissions(
  permissions: Record<string, string[]>,
): BackendPermissionMapping {
  const backendPermissions = flattenBackendPermissions(permissions)
  const mapped = new Set<AppPermission>()
  const unmappedBackendPermissions: string[] = []

  for (const backendPermission of backendPermissions) {
    // Existing MSW/test fixtures currently use canonical frontend permissions.
    // Accepting these keeps local development stable while mocks are migrated.
    if (canonicalAppPermissions.has(backendPermission)) {
      mapped.add(backendPermission as AppPermission)
      continue
    }

    const translated = VERIFIED_BACKEND_PERMISSION_MAP[backendPermission]
    if (translated) {
      mapped.add(translated)
      continue
    }

    unmappedBackendPermissions.push(backendPermission)
  }

  return {
    permissions: [...mapped],
    backendPermissions,
    unmappedBackendPermissions,
  }
}
