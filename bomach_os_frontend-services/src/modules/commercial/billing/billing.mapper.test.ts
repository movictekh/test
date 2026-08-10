import { describe, expect, it } from 'vitest'

import { mapInvoice, mapPayment, mapPaymentSubmission } from './billing.mapper'

describe('billing mapper', () => {
  it('maps backend invoice decimals and nested service', () => {
    const invoice = mapInvoice({
      id: 3,
      invoice_number: 'SRV-2026-08-ABC',
      client_id: 9,
      quote_id: 4,
      service_request_id: 8,
      service: { id: 2, name: 'Survey' },
      issue_date: '2026-08-10',
      due_date: '2026-08-24',
      subtotal: '100000.00',
      tax_rate: '7.50',
      tax_amount: '7500.00',
      total_amount: '107500.00',
      amount_paid: '30000.00',
      balance: '77500.00',
      payment_progress: 27.9,
      status: 'partially_paid',
      activation_threshold_amount: '30000.00',
      activation_threshold_met_at: '2026-08-11T10:00:00Z',
      items: [],
      created_at: '2026-08-10T10:00:00Z',
      updated_at: '2026-08-11T10:00:00Z',
      created_by_id: 1,
    })

    expect(invoice.totalAmount).toBe(107500)
    expect(invoice.balance).toBe(77500)
    expect(invoice.status).toBe('partially_paid')
    expect(invoice.serviceName).toBe('Survey')
    expect(invoice.activationThresholdMetAt).toBeTruthy()
  })

  it('maps real payment method enum', () => {
    expect(
      mapPayment({
        id: 1,
        payment_reference: 'PAY-1',
        invoice_id: 3,
        amount: '1000.00',
        payment_method: 'bank_transfer',
        payment_date: '2026-08-10',
        created_by_id: 1,
      }).paymentMethod,
    ).toBe('bank_transfer')
  })

  it('normalizes display status returned by submission schema', () => {
    expect(
      mapPaymentSubmission({
        id: 1,
        reference: 'SUB-1',
        invoice_number: 'INV-1',
        amount: '1000',
        payment_method: 'bank_transfer',
        payment_date: '2026-08-10',
        proof_of_payment: 'https://example.test/proof.pdf',
        status: 'Pending Review',
        rejection_reason: '',
        created_at: '2026-08-10T10:00:00Z',
      }).status,
    ).toBe('pending')
  })
})
