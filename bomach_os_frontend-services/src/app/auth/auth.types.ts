import type { AppPermission } from '@/app/permissions'
import type { AuthAccessIssue } from '@/modules/auth/errors/auth-access-error'
import type { LoginCredentials, LoginResult } from '@/modules/auth/types/auth.types'

export const APP_ROLES = [
  'CEO',
  'SERVICE_ADMINISTRATOR',
  'HEAD_OF_OPERATIONS',
  'SERVICE_MANAGER',
  'FINANCE',
  'SALES_CSRC',
  'CIVIL_ENGINEER',
  'LAND_SURVEYOR',
  'PROPERTY_MANAGER',
  'PROJECT_MANAGER',
  'UNKNOWN',
] as const

export type AppRole = (typeof APP_ROLES)[number]
export const AUTH_USER_KINDS = ['staff'] as const
export type AuthUserKind = (typeof AUTH_USER_KINDS)[number]

export interface AuthUser {
  id: string
  name: string
  email: string
  username: string
  initials: string
  role: AppRole
  roleLabel: string
  kind: AuthUserKind
  permissions: AppPermission[]
  backendPermissions: string[]
  isVerified: boolean
}

export interface AuthContextValue {
  user: AuthUser | null
  isAuthenticated: boolean
  isLoading: boolean
  accessIssue: AuthAccessIssue | null
  login: (credentials: LoginCredentials) => Promise<LoginResult>
  verifyTwoFactor: (sessionToken: string, code: string) => Promise<AuthUser>
  signOut: () => Promise<void>
}
