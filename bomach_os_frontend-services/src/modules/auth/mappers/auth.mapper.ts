import type { AppRole } from '@/app/auth/auth.types'

import type { RoleResponseDto, UserResponseDto } from '../types/auth.contracts'
import type { AuthenticatedUser } from '../types/auth.types'
import { mapBackendPermissions } from './auth-permissions.mapper'

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
  }

  return aliases[normalized] ?? 'UNKNOWN'
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
  const { permissions, backendPermissions } = mapBackendPermissions(role.permissions)

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
