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

    expect(hasPermission(user, PERMISSIONS.dashboardRead)).toBe(false)
    expect(hasPermission(user, PERMISSIONS.serviceCreate)).toBe(false)
    expect(hasPermission(user, PERMISSIONS.realEstateRead)).toBe(false)
  })

  it('does not grant access from a frontend role name', () => {
    expect(hasPermission(makeUser([], 'SERVICE_ADMINISTRATOR'), PERMISSIONS.serviceCreate)).toBe(
      false,
    )

    expect(hasPermission(makeUser([], 'HEAD_OF_OPERATIONS'), PERMISSIONS.orderUpdate)).toBe(false)
  })

  it('grants only explicit backend-provided permissions', () => {
    const user = makeUser([PERMISSIONS.dashboardRead, PERMISSIONS.orderRead, PERMISSIONS.taskRead])

    expect(hasPermission(user, PERMISSIONS.dashboardRead)).toBe(true)
    expect(hasPermission(user, PERMISSIONS.orderRead)).toBe(true)
    expect(hasPermission(user, PERMISSIONS.taskRead)).toBe(true)
    expect(hasPermission(user, PERMISSIONS.orderUpdate)).toBe(false)
    expect(hasPermission(user, PERMISSIONS.realEstateRead)).toBe(false)
  })

  it('supports any-permission checks using only the backend permission set', () => {
    const user = makeUser([PERMISSIONS.requestRead])

    expect(hasPermissions(user, [PERMISSIONS.paymentConfirm, PERMISSIONS.requestRead], 'any')).toBe(
      true,
    )
  })
})
