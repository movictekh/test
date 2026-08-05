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
  'CLIENT',
] as const

export type AppRole = (typeof APP_ROLES)[number]

export const AUTH_USER_KINDS = ['staff', 'client'] as const

export type AuthUserKind = (typeof AUTH_USER_KINDS)[number]

export const MOCK_AUTH_PROFILES = ['service-administrator', 'client'] as const

export type MockAuthProfile = (typeof MOCK_AUTH_PROFILES)[number]

export interface AuthUser {
  id: string
  name: string
  email: string
  initials: string
  role: AppRole
  kind: AuthUserKind
}

export interface AuthContextValue {
  user: AuthUser | null
  isAuthenticated: boolean
  isLoading: boolean
  signInAsProfile: (profile: MockAuthProfile) => Promise<AuthUser>
  signOut: () => Promise<void>
}
