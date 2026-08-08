import { describe, expect, it } from 'vitest'

import { mapPricingConfigDto, mapSaveCalculatorInput } from './pricing-config.mapper'

describe('pricing config pricing types', () => {
  it.each(['fixed', 'unit_rate', 'area_rate', 'percentage', 'formula'] as const)(
    'sends %s to the backend without collapsing it to formula',
    (pricingType) => {
      const payload = mapSaveCalculatorInput({
        name: 'Pricing',
        code: 'CALC',
        serviceId: '1',
        description: '',
        pricingType,
        status: 'draft',
        variables: [],
        charges:
          pricingType === 'formula'
            ? [{ id: 'formula', label: 'Formula', kind: 'formula', value: 'quantity * rate' }]
            : [],
        sampleTotal: 0,
      })

      expect(payload.pricing_type).toBe(pricingType)
      expect(payload.formula).toBe(pricingType === 'formula' ? 'quantity * rate' : '')
    },
  )

  it('keeps the backend pricing type when mapping a loaded config', () => {
    const result = mapPricingConfigDto({
      id: 3,
      service_id: 8,
      service_name: 'Survey',
      name: 'Area pricing',
      version: 1,
      pricing_type: 'area_rate',
      formula: '',
      tax_rate: '0',
      deposit_percent: '0',
      discount_approval_threshold_percent: '0',
      status: 'active',
      is_active: true,
      field_count: 0,
      created_by_id: 1,
      created_at: '2026-08-08T00:00:00Z',
      updated_at: '2026-08-08T00:00:00Z',
      fields: [],
    })

    expect(result.pricingType).toBe('area_rate')
  })
})
