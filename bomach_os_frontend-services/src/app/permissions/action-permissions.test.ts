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
    const staff = user([PERMISSIONS.serviceInvoicesList, PERMISSIONS.ordersList])
    expect(canPerformAction(staff, 'paymentsCreate')).toBe(false)
    expect(canPerformAction(staff, 'orderUpdate')).toBe(false)
  })

  it('allows only the explicit backend capability', () => {
    const staff = user([
      PERMISSIONS.serviceInvoicesList,
      PERMISSIONS.paymentsCreate,
      PERMISSIONS.ordersList,
      PERMISSIONS.ordersUpdate,
    ])

    expect(canPerformAction(staff, 'paymentsCreate')).toBe(true)
    expect(canPerformAction(staff, 'orderUpdate')).toBe(true)
    expect(canPerformAction(staff, 'deliverableApprove')).toBe(false)
  })
})
