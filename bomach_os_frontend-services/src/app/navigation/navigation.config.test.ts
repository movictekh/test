import { describe, expect, it } from 'vitest'

import { operationsNavigation } from './navigation.config'
import { PERMISSIONS } from '@/app/permissions'

describe('specialized services navigation', () => {
  it('uses the required specialized services labels', () => {
    const group = operationsNavigation.find((item) => item.id === 'specialized-services')
    expect(group?.label).toBe('Specialized Services')
    expect(group?.items.map((item) => item.label)).toEqual([
      'Real Estate Inventory',
      'Survey / Engineering / Others',
    ])
  })

  it('declares backend capability requirements without assigning them to roles', () => {
    const group = operationsNavigation.find((item) => item.id === 'specialized-services')
    const realEstate = group?.items.find((item) => item.id === 'real-estate-inventory')
    const surveyEngineering = group?.items.find((item) => item.id === 'survey-engineering-others')

    expect(realEstate?.permissions).toEqual([PERMISSIONS.realEstateRead])
    expect(surveyEngineering?.permissions).toEqual([PERMISSIONS.ordersList])
  })
})
