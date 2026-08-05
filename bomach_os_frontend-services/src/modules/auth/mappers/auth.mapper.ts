import { APP_PERMISSION_VALUES, type AppPermission } from '@/app/permissions'
import type { AppRole, AuthUserKind } from '@/app/auth/auth.types'

import type { RoleResponseDto, UserResponseDto } from '../types/auth.contracts'
import type { AuthenticatedUser } from '../types/auth.types'

const knownPermissions = new Set<string>(APP_PERMISSION_VALUES)

function normaliseRoleName(value: string): AppRole {
  const normalized = value
    .trim()
    .toUpperCase()
    .replace(/[\s/-]+/g, '_')

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
    CLIENT: 'CLIENT',
  }

  return aliases[normalized] ?? 'SERVICE_MANAGER'
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
  role: RoleResponseDto | null,
  kind: AuthUserKind,
): AuthenticatedUser {
  const backendPermissions = role ? flattenPermissions(role.permissions) : []
  const permissions = backendPermissions.filter((permission): permission is AppPermission =>
    knownPermissions.has(permission),
  )
  const firstName = user.first_name?.trim() || ''
  const lastName = user.last_name?.trim() || ''
  const name = [firstName, lastName].filter(Boolean).join(' ') || user.username
  const appRole = kind === 'client' ? 'CLIENT' : normaliseRoleName(role?.name ?? '')

  return {
    id: String(user.id),
    name,
    email: user.email,
    username: user.username,
    initials: getInitials(user.first_name, user.last_name, user.username),
    role: appRole,
    roleLabel: kind === 'client' ? 'Client' : role?.name || 'Staff User',
    kind,
    permissions,
    backendPermissions,
    isVerified: user.is_verified,
  }
}
