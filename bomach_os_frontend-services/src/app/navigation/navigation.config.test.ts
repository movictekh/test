import { describe, expect, it } from 'vitest'

import { operationsNavigation } from './navigation.config'
import { PERMISSIONS, rolePermissions } from '@/app/permissions'

describe('specialized services navigation', () => {
  it('uses the exact specialized services prototype labels', () => {
    const group = operationsNavigation.find((item) => item.id === 'specialized-services')
    expect(group?.label).toBe('Specialized Services')
    expect(group?.items.map((item) => item.label)).toEqual([
      'Real Estate Inventory',
      'Survey / Engineering / Others',
    ])
  })

  it('exposes real estate inventory to operational management roles', () => {
    expect(rolePermissions.SERVICE_ADMINISTRATOR).toContain(PERMISSIONS.realEstateRead)
    expect(rolePermissions.HEAD_OF_OPERATIONS).toContain(PERMISSIONS.realEstateRead)
    expect(rolePermissions.SERVICE_MANAGER).toContain(PERMISSIONS.realEstateRead)
  })
})
