import { describe, expect, it } from 'vitest'

import { getInvoiceCapabilities } from './invoice-capabilities'
import type { Invoice } from './billing.types'

const invoice = (overrides: Partial<Invoice>): Invoice => ({
  id: 1,
  invoiceNumber: 'INV-1',
  clientId: 1,
  clientName: 'Client',
  quoteId: 1,
  serviceRequestId: 1,
  serviceId: 1,
  serviceName: 'Service',
  orderId: null,
  orderNumber: '',
  issueDate: '2026-08-10',
  dueDate: '2026-08-20',
  subtotal: 100,
  taxRate: 0,
  taxAmount: 0,
  totalAmount: 100,
  amountPaid: 0,
  balance: 100,
  paymentProgress: 0,
  status: 'draft',
  paymentSchedule: '',
  paymentInstructions: '',
  activationThresholdAmount: 30,
  activationThresholdMetAt: null,
  notes: '',
  items: [],
  createdAt: '',
  updatedAt: '',
  createdById: 1,
  ...overrides,
})

describe('invoice capabilities', () => {
  it('draft can edit/send/cancel but not record payment', () => {
    expect(getInvoiceCapabilities(invoice({ status: 'draft' }))).toMatchObject({
      edit: true,
      send: true,
      cancel: true,
      recordPayment: false,
    })
  })

  it('partially paid can record payment but cannot cancel', () => {
    expect(
      getInvoiceCapabilities(
        invoice({
          status: 'partially_paid',
          amountPaid: 30,
          balance: 70,
        }),
      ),
    ).toMatchObject({
      recordPayment: true,
      cancel: false,
    })
  })

  it('threshold readiness is independent of full payment', () => {
    expect(
      getInvoiceCapabilities(
        invoice({
          status: 'partially_paid',
          amountPaid: 30,
          balance: 70,
          activationThresholdMetAt: '2026-08-10T10:00:00Z',
        }),
      ).readyForServiceOrder,
    ).toBe(true)
  })
})
