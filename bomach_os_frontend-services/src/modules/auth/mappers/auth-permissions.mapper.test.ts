import { describe, expect, it } from 'vitest'

import { PERMISSIONS } from '@/app/permissions'

import { flattenBackendPermissions, mapBackendPermissions } from './auth-permissions.mapper'

describe('backend permission mapping', () => {
  it('normalizes backend resource/action capabilities', () => {
    expect(
      flattenBackendPermissions({
        ' Orders ': [' VIEW ', 'List'],
      }),
    ).toEqual(['orders.view', 'orders.list'])
  })

  it('maps catalog-verified order capabilities to frontend read permission', () => {
    const result = mapBackendPermissions({
      orders: ['view', 'list'],
    })

    expect(result.permissions).toEqual([PERMISSIONS.orderRead])
    expect(result.unmappedBackendPermissions).toEqual([])
  })

  it('maps catalog-verified service request capabilities', () => {
    const result = mapBackendPermissions({
      service_requests: ['view', 'list', 'create'],
    })

    expect(result.permissions).toEqual([PERMISSIONS.requestRead, PERMISSIONS.requestCreate])
  })

  it('keeps valid but unmapped backend capabilities fail-closed', () => {
    const result = mapBackendPermissions({
      roles: ['view_own'],
      employees: ['view_own', 'update_own'],
    })

    expect(result.permissions).toEqual([])
    expect(result.unmappedBackendPermissions).toEqual([
      'roles.view_own',
      'employees.view_own',
      'employees.update_own',
    ])
  })

  it('temporarily accepts canonical frontend permissions used by MSW fixtures', () => {
    const result = mapBackendPermissions({
      order: ['read', 'update'],
    })

    expect(result.permissions).toEqual([PERMISSIONS.orderRead, PERMISSIONS.orderUpdate])
  })
})
