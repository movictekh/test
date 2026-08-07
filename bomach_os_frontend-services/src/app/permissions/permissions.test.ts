import { describe, expect, it } from 'vitest'

import type { AuthUser } from '@/app/auth'

import { PERMISSIONS, hasPermission, hasPermissions } from './permissions'

function makeUser(
  permissions: AuthUser['permissions'],
  role: AuthUser['role'] = 'SERVICE_ADMINISTRATOR',
): AuthUser {
  return {
    id: 'staff-1',
    name: 'Staff User',
    email: 'staff@bomach.local',
    username: 'staff',
    initials: 'SU',
    role,
    roleLabel: role,
    kind: 'staff',
    permissions,
    backendPermissions: [...permissions],
    isVerified: true,
  }
}

describe('permission helpers', () => {
  it('treats an empty backend permission payload as zero access', () => {
    const user = makeUser([])
    expect(hasPermission(user, PERMISSIONS.dashboardView)).toBe(false)
    expect(hasPermission(user, PERMISSIONS.servicesCreate)).toBe(false)
  })

  it('does not grant access from a frontend role name', () => {
    expect(hasPermission(makeUser([], 'SERVICE_ADMINISTRATOR'), PERMISSIONS.servicesCreate)).toBe(
      false,
    )
    expect(hasPermission(makeUser([], 'HEAD_OF_OPERATIONS'), PERMISSIONS.ordersUpdate)).toBe(false)
  })

  it('preserves list and view as separate capabilities', () => {
    const user = makeUser([PERMISSIONS.servicesList])
    expect(hasPermission(user, PERMISSIONS.servicesList)).toBe(true)
    expect(hasPermission(user, PERMISSIONS.servicesView)).toBe(false)
  })

  it('grants only explicit backend-provided permissions', () => {
    const user = makeUser([
      PERMISSIONS.dashboardView,
      PERMISSIONS.ordersList,
      PERMISSIONS.tasksList,
    ])
    expect(hasPermission(user, PERMISSIONS.dashboardView)).toBe(true)
    expect(hasPermission(user, PERMISSIONS.ordersList)).toBe(true)
    expect(hasPermission(user, PERMISSIONS.tasksList)).toBe(true)
    expect(hasPermission(user, PERMISSIONS.ordersUpdate)).toBe(false)
  })

  it('supports any-permission checks', () => {
    const user = makeUser([PERMISSIONS.serviceRequestsList])
    expect(
      hasPermissions(user, [PERMISSIONS.paymentsCreate, PERMISSIONS.serviceRequestsList], 'any'),
    ).toBe(true)
  })
})
