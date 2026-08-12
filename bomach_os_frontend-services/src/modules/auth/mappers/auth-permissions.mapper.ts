import { APP_PERMISSION_VALUES, type AppPermission } from '@/app/permissions/permission.types'
import { PERMISSIONS } from '@/app/permissions'

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

  if (
    backendPermissions.includes('documents.view') ||
    backendPermissions.includes('orders.view') ||
    backendPermissions.includes('orders.list')
  ) {
    granted.add(PERMISSIONS.deliverableRead)
  }

  return {
    permissions: [...granted],
    backendPermissions,
    unmappedBackendPermissions,
  }
}
