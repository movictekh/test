import { describe, expect, it } from 'vitest'
import { mapSaveCalculatorInput } from './pricing-config.mapper'

describe('pricing config mapper', () => {
  it('maps formula and percentages to exact backend fields', () => {
    expect(
      mapSaveCalculatorInput({
        name: 'Survey pricing',
        code: 'CALC-1',
        serviceId: '9',
        description: '',
        pricingType: 'formula',
        status: 'active',
        variables: [],
        charges: [
          { id: 'f', label: 'Formula', kind: 'formula', value: 'quantity * rate' },
          { id: 'd', label: 'Deposit', kind: 'percentage', value: 70 },
          { id: 't', label: 'Tax', kind: 'percentage', value: 7.5 },
          { id: 'a', label: 'Approval', kind: 'percentage', value: 5 },
        ],
        sampleTotal: 0,
      }),
    ).toMatchObject({
      pricing_type: 'formula',
      formula: 'quantity * rate',
      deposit_percent: 70,
      tax_rate: 7.5,
      discount_approval_threshold_percent: 5,
      status: 'active',
      is_active: true,
    })
  })
})
