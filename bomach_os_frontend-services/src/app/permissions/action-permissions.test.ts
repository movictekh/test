import { describe, expect, it } from 'vitest'

import type { AuthUser } from '@/app/auth'

import { PERMISSIONS } from './permissions'
import { canPerformAction } from './action-permissions'

function user(permissions: AuthUser['permissions']): AuthUser {
  return {
    id: '1',
    name: 'Staff',
    email: 'staff@bomach.local',
    username: 'staff',
    initials: 'ST',
    role: 'UNKNOWN',
    roleLabel: 'Backend Role',
    kind: 'staff',
    permissions,
    backendPermissions: [...permissions],
    isVerified: true,
  }
}

describe('action permissions', () => {
  it('does not infer write access from role or read access', () => {
    const staff = user([PERMISSIONS.invoiceRead, PERMISSIONS.orderRead])
    expect(canPerformAction(staff, 'paymentConfirm')).toBe(false)
    expect(canPerformAction(staff, 'orderUpdate')).toBe(false)
  })

  it('allows only the explicit backend capability', () => {
    const staff = user([
      PERMISSIONS.invoiceRead,
      PERMISSIONS.paymentConfirm,
      PERMISSIONS.orderRead,
      PERMISSIONS.orderUpdate,
    ])

    expect(canPerformAction(staff, 'paymentConfirm')).toBe(true)
    expect(canPerformAction(staff, 'orderUpdate')).toBe(true)
    expect(canPerformAction(staff, 'deliverableApprove')).toBe(false)
  })
})
