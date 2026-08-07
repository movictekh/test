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

  it('preserves list and view as different permissions', () => {
    const result = mapBackendPermissions({
      orders: ['view', 'list'],
    })

    expect(result.permissions).toEqual([PERMISSIONS.ordersView, PERMISSIONS.ordersList])
    expect(result.unmappedBackendPermissions).toEqual([])
  })

  it('preserves exact service request capabilities', () => {
    const result = mapBackendPermissions({
      service_requests: ['view', 'list', 'create'],
    })

    expect(result.permissions).toEqual([
      PERMISSIONS.serviceRequestsView,
      PERMISSIONS.serviceRequestsList,
      PERMISSIONS.serviceRequestsCreate,
    ])
  })

  it('preserves exact Service Administration capabilities', () => {
    const result = mapBackendPermissions({
      services: ['list', 'view', 'create', 'update'],
      service_pricing_configs: ['list', 'view'],
    })

    expect(result.permissions).toEqual([
      PERMISSIONS.servicesList,
      PERMISSIONS.servicesView,
      PERMISSIONS.servicesCreate,
      PERMISSIONS.servicesUpdate,
      PERMISSIONS.servicePricingConfigsList,
      PERMISSIONS.servicePricingConfigsView,
    ])
  })

  it('keeps irrelevant or unknown backend capabilities fail-closed', () => {
    const result = mapBackendPermissions({
      roles: ['view_own'],
      employees: ['view_own', 'update_own'],
      unknown_resource: ['read'],
    })

    expect(result.permissions).toEqual([])
    expect(result.unmappedBackendPermissions).toEqual([
      'roles.view_own',
      'employees.view_own',
      'employees.update_own',
      'unknown_resource.read',
    ])
  })
})
