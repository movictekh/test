import { describe, expect, it } from 'vitest'

import { validatePaymentInput } from './payment.validation'
import type { Invoice } from './billing.types'

const invoice = { balance: 500 } as Invoice

describe('payment validation', () => {
  it('blocks overpayment and requires a transaction reference', () => {
    const errors = validatePaymentInput(
      {
        invoiceId: 1,
        amount: 600,
        paymentMethod: 'bank_transfer',
        paymentDate: '2026-08-10',
        transactionReference: '',
        notes: '',
      },
      invoice,
    )

    expect(errors.amount).toBeTruthy()
    expect(errors.transactionReference).toBeTruthy()
  })
})
