import { describe, expect, it } from 'vitest'

import type { CommercialInvoice, CommercialQuotation } from '../types/commercial.types'
import {
  deriveInvoiceStatus,
  getInvoiceEligibleQuotations,
  validatePaymentInput,
} from './commercial-finance.rules'

const quote = (id: string, status: CommercialQuotation['status']) =>
  ({ id, status }) as CommercialQuotation

const invoice = {
  id: 'INV-1',
  quotationId: 'Q-2',
  total: 1000,
  amountPaid: 200,
  balance: 800,
  status: 'Part Paid',
} as CommercialInvoice

describe('commercial finance rules', () => {
  it('invoices accepted quotations only once', () => {
    expect(
      getInvoiceEligibleQuotations(
        [quote('Q-1', 'Sent'), quote('Q-2', 'Accepted'), quote('Q-3', 'Accepted')],
        [invoice],
      ).map((item) => item.id),
    ).toEqual(['Q-3'])
  })

  it('prevents payment over-allocation', () => {
    const errors = validatePaymentInput(
      {
        invoiceId: invoice.id,
        amount: 900,
        method: 'Bank Transfer',
        reference: 'TRF-1',
        paidAt: '2026-08-06',
        note: '',
      },
      invoice,
    )

    expect(errors.amount).toBeDefined()
  })

  it('derives invoice collection states', () => {
    expect(deriveInvoiceStatus(1000, 0, '2026-08-20', new Date('2026-08-06'))).toBe('Issued')
    expect(deriveInvoiceStatus(1000, 200, '2026-08-20')).toBe('Part Paid')
    expect(deriveInvoiceStatus(1000, 1000, '2026-08-20')).toBe('Paid')
    expect(deriveInvoiceStatus(1000, 0, '2026-08-01', new Date('2026-08-06'))).toBe('Overdue')
  })
})
