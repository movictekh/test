import type { AuthUser } from '@/app/auth'
import { hasPermissions } from '@/app/permissions'

import type { NavigationGroup, NavigationItem } from './navigation.types'

function canSeeNavigationItem(user: AuthUser | null, item: NavigationItem): boolean {
  return hasPermissions(user, item.permissions ?? [], item.permissionMode ?? 'all')
}

export function getVisibleNavigation(
  groups: readonly NavigationGroup[],
  user: AuthUser | null,
): NavigationGroup[] {
  return groups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => canSeeNavigationItem(user, item)),
    }))
    .filter((group) => group.items.length > 0)
}

export function isNavigationItemActive(pathname: string, item: NavigationItem): boolean {
  if (!item.to) {
    return false
  }

  return item.exact ? pathname === item.to : pathname.startsWith(item.to)
}
