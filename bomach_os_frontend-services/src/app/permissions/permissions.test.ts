import { describe, expect, it } from 'vitest'

import type { AuthUser } from '@/app/auth'

import { PERMISSIONS, hasPermission, hasPermissions } from './permissions'

const serviceAdministrator: AuthUser = {
  id: 'service-admin',
  name: 'Service Administrator',
  email: 'service.admin@bomach.local',
  username: 'service.admin',
  initials: 'SA',
  role: 'SERVICE_ADMINISTRATOR',
  roleLabel: 'Service Administrator',
  kind: 'staff',
  permissions: [],
  backendPermissions: [],
  isVerified: true,
}

const client: AuthUser = {
  id: 'client',
  name: 'Client',
  email: 'client@bomach.local',
  username: 'chief.okafor',
  initials: 'CL',
  role: 'CLIENT',
  roleLabel: 'Client',
  kind: 'client',
  permissions: [],
  backendPermissions: [],
  isVerified: true,
}

describe('permission helpers', () => {
  it('allows a service administrator to create a service', () => {
    expect(hasPermission(serviceAdministrator, PERMISSIONS.serviceCreate)).toBe(true)
  })

  it('gives the service administrator full read/write access across the app', () => {
    expect(hasPermission(serviceAdministrator, PERMISSIONS.realEstateRead)).toBe(true)
    expect(hasPermission(serviceAdministrator, PERMISSIONS.portalRead)).toBe(true)
    expect(hasPermission(serviceAdministrator, PERMISSIONS.approvalAct)).toBe(true)
    expect(hasPermission(serviceAdministrator, PERMISSIONS.invoiceCreate)).toBe(true)
    expect(hasPermission(serviceAdministrator, PERMISSIONS.paymentConfirm)).toBe(true)
    expect(hasPermission(serviceAdministrator, PERMISSIONS.orderUpdate)).toBe(true)
    expect(hasPermission(serviceAdministrator, PERMISSIONS.taskUpdate)).toBe(true)
    expect(hasPermission(serviceAdministrator, PERMISSIONS.deliverableApprove)).toBe(true)
    expect(hasPermission(serviceAdministrator, PERMISSIONS.quoteApprove)).toBe(true)
  })

  it('does not allow a client to read internal audit records', () => {
    expect(hasPermission(client, PERMISSIONS.auditRead)).toBe(false)
  })

  it('supports any-permission checks', () => {
    expect(
      hasPermissions(
        serviceAdministrator,
        [PERMISSIONS.paymentConfirm, PERMISSIONS.requestRead],
        'any',
      ),
    ).toBe(true)
  })
})
