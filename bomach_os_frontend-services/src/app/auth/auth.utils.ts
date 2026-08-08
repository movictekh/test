import type { AppRole, AuthUser, AuthUserKind } from './auth.types'

const roleLabels: Record<AppRole, string> = {
  CEO: 'CEO / Founder',
  SERVICE_ADMINISTRATOR: 'Service Administrator',
  HEAD_OF_OPERATIONS: 'Head of Operations',
  SERVICE_MANAGER: 'Service Manager',
  FINANCE: 'Finance and Accounts',
  SALES_CSRC: 'Sales / CSRC Officer',
  CIVIL_ENGINEER: 'Civil Engineer',
  LAND_SURVEYOR: 'Land Surveyor',
  PROPERTY_MANAGER: 'Property Manager',
  PROJECT_MANAGER: 'Project Manager',
  UNKNOWN: 'Staff User',
}

export function formatRoleLabel(role: AppRole, roleLabel?: string): string {
  return roleLabel || roleLabels[role]
}

export function isUserKind(user: AuthUser | null, allowedKinds: readonly AuthUserKind[]): boolean {
  return Boolean(user && allowedKinds.includes(user.kind))
}
