import { describe, expect, it, vi } from 'vitest'

import type { AuthContextValue, AuthUser } from '@/app/auth'

import { requireRoutePermission } from './route-permissions'

const noOpAsync = vi.fn(() => Promise.resolve(undefined))

function makeUser(permissions: AuthUser['permissions']): AuthUser {
  return {
    id: '1',
    name: 'Service Admin',
    email: 'service.admin@bomach.local',
    username: 'service.admin',
    initials: 'SA',
    role: 'SERVICE_ADMINISTRATOR',
    roleLabel: 'Service Administrator',
    kind: 'staff',
    permissions,
    backendPermissions: permissions,
    isVerified: true,
  }
}

function makeAuth(overrides: Partial<AuthContextValue> = {}): AuthContextValue {
  return {
    user: null,
    isAuthenticated: false,
    isLoading: false,
    accessIssue: null,
    login: vi.fn(),
    verifyTwoFactor: vi.fn(),
    signOut: noOpAsync,
    ...overrides,
  }
}

describe('requireRoutePermission', () => {
  it('does not deny access while authentication is still bootstrapping', () => {
    const result = requireRoutePermission({
      auth: makeAuth({
        user: null,
        isAuthenticated: false,
        isLoading: true,
      }),
      permissions: ['service.read'],
    })

    expect(result).toBeUndefined()
  })

  it('does not convert an unauthenticated state into a permission denial', () => {
    const result = requireRoutePermission({
      auth: makeAuth(),
      permissions: ['service.read'],
    })

    expect(result).toBeUndefined()
  })

  it('allows an authenticated user with the required permission', () => {
    const user = makeUser(['service.read'])

    const result = requireRoutePermission({
      auth: makeAuth({
        user,
        isAuthenticated: true,
      }),
      permissions: ['service.read'],
    })

    expect(result).toBeUndefined()
  })

  it('returns a forbidden redirect only after auth is resolved and permission is missing', () => {
    const user = makeUser(['dashboard.read'])

    const result = requireRoutePermission({
      auth: makeAuth({
        user,
        isAuthenticated: true,
      }),
      permissions: ['service.read'],
    })

    expect(result).toBeDefined()
    expect(result).toMatchObject({
      options: {
        to: '/forbidden',
        replace: true,
      },
    })
  })
})
