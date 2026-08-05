import type { AppRole, AuthUserKind } from '@/app/auth/auth.types'
import type { AppPermission } from '@/app/permissions'

export interface LoginCredentials {
  email: string
  password: string
}

export type LoginResult =
  | { type: 'authenticated'; user?: AuthenticatedUser }
  | { type: 'two-factor-required'; sessionToken: string; detail: string }

export interface AuthenticatedUser {
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
