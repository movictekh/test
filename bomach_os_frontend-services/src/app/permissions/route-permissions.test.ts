import { describe, expect, it, vi } from 'vitest'

import type { AuthContextValue, AuthUser } from '@/app/auth'

import { PERMISSIONS } from './permissions'
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
      permissions: [PERMISSIONS.servicesList],
    })

    expect(result).toBeUndefined()
  })

  it('redirects a resolved unauthenticated state to login instead of allowing the route to mount', () => {
    const result = requireRoutePermission({
      auth: makeAuth(),
      permissions: [PERMISSIONS.servicesList],
      locationHref: '/app/service-catalogue',
    })

    expect(result).toBeDefined()
    expect(result).toMatchObject({
      options: {
        to: '/login',
        search: {
          redirect: '/app/service-catalogue',
        },
        replace: true,
      },
    })
  })

  it('allows an authenticated user with the required permission', () => {
    const user = makeUser([PERMISSIONS.servicesList])

    const result = requireRoutePermission({
      auth: makeAuth({
        user,
        isAuthenticated: true,
      }),
      permissions: [PERMISSIONS.servicesList],
    })

    expect(result).toBeUndefined()
  })

  it('returns a forbidden redirect only after auth is resolved and permission is missing', () => {
    const user = makeUser([PERMISSIONS.dashboardView])

    const result = requireRoutePermission({
      auth: makeAuth({
        user,
        isAuthenticated: true,
      }),
      permissions: [PERMISSIONS.servicesList],
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
