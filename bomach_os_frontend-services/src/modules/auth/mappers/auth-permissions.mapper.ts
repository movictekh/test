import { APP_PERMISSION_VALUES, type AppPermission } from '@/app/permissions/permission.types'

const appPermissions = new Set<string>(APP_PERMISSION_VALUES)

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

/**
 * Backend permissions are canonical.
 *
 * There is intentionally no resource/action synonym translation here.
 */
export function mapBackendPermissions(
  permissions: Record<string, string[]>,
): BackendPermissionMapping {
  const backendPermissions = flattenBackendPermissions(permissions)
  const granted = new Set<AppPermission>()
  const unmappedBackendPermissions: string[] = []

  for (const backendPermission of backendPermissions) {
    if (appPermissions.has(backendPermission)) {
      granted.add(backendPermission as AppPermission)
    } else {
      unmappedBackendPermissions.push(backendPermission)
    }
  }

  return {
    permissions: [...granted],
    backendPermissions,
    unmappedBackendPermissions,
  }
}
