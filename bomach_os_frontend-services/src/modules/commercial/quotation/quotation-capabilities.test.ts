import { describe, expect, it } from 'vitest'
import { getQuotationCapabilities } from './quotation-capabilities'

describe('quotation capabilities', () => {
  it('maps backend lifecycle', () => {
    expect(getQuotationCapabilities('awaiting_approval').approve).toBe(true)
    expect(getQuotationCapabilities('sent').clientRespond).toBe(true)
    expect(getQuotationCapabilities('accepted').createInvoice).toBe(true)
    expect(getQuotationCapabilities('rejected').revise).toBe(true)
    expect(getQuotationCapabilities('rejected').edit).toBe(false)
    expect(getQuotationCapabilities('expired').revise).toBe(true)
  })
})
