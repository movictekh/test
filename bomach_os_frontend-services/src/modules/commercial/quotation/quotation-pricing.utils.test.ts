import { describe, expect, it } from 'vitest'
import { calculateQuotationPreview, validateQuotationPricing } from './quotation-pricing.utils'

describe('quotation pricing', () => {
  it('matches backend ordering: discount before tax, deposit after total', () => {
    expect(
      calculateQuotationPreview({
        serviceFee: 100000,
        otherCharges: 20000,
        discount: 10000,
        taxRate: 7.5,
        depositPercent: 30,
      }),
    ).toEqual({
      subtotal: 120000,
      taxable: 110000,
      taxAmount: 8250,
      amount: 118250,
      depositAmount: 35475,
    })
  })

  it('rejects discount above subtotal and invalid percentages', () => {
    const e = validateQuotationPricing({
      serviceFee: 100,
      otherCharges: 0,
      discount: 101,
      taxRate: 101,
      depositPercent: -1,
    })
    expect(e.discount).toBeTruthy()
    expect(e.taxRate).toBeTruthy()
    expect(e.depositPercent).toBeTruthy()
  })
})
