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
  const targetPath = getNavigationItemPath(item)

  return item.exact ? pathname === targetPath : pathname.startsWith(targetPath)
}

export function findNavigationItemByPath(
  groups: readonly NavigationGroup[],
  pathname: string,
): NavigationItem | null {
  for (const group of groups) {
    for (const item of group.items) {
      if (isNavigationItemActive(pathname, item)) {
        return item
      }
    }
  }

  return null
}

export function getNavigationItemPath(item: NavigationItem): string {
  if (!item.params) {
    return item.to
  }

  let path: string = item.to

  for (const [key, value] of Object.entries(item.params)) {
    path = path.replace(`$${key}`, value)
  }

  return path
}

export function getAuthenticatedNavigationPath(
  groups: readonly NavigationGroup[],
  user: AuthUser | null,
  preferredPath?: string,
): string | null {
  if (!user) return null

  if (preferredPath) {
    const preferredItem = findNavigationItemByPath(groups, preferredPath)

    if (preferredItem && canSeeNavigationItem(user, preferredItem)) {
      return getNavigationItemPath(preferredItem)
    }
  }

  for (const group of groups) {
    for (const item of group.items) {
      if (canSeeNavigationItem(user, item)) {
        return getNavigationItemPath(item)
      }
    }
  }

  return null
}
