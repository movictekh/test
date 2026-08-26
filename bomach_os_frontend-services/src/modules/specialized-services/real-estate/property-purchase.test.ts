import { describe, expect, it } from 'vitest'
import { mapPropertyPurchase, mapPurchaseClient } from './property-purchase.api'

describe('property purchase API mapping', () => {
  it('maps CRM client search rows', () => {
    expect(
      mapPurchaseClient({
        id: 7,
        user_id: 17,
        full_name: 'Ada Buyer',
        email: 'ada@example.com',
        phone: '+2348012345678',
        company_name: 'Buyer Ltd',
      }),
    ).toEqual({
      id: 7,
      userId: 17,
      fullName: 'Ada Buyer',
      email: 'ada@example.com',
      phone: '+2348012345678',
      companyName: 'Buyer Ltd',
    })
  })

  it('maps snapshotted property purchase terms', () => {
    const purchase = mapPropertyPurchase({
      id: 4,
      property_id: 10,
      property_name: 'Plot A-01',
      estate_id: 2,
      estate_name: 'Oak Estate',
      client_id: 7,
      client_user_id: 17,
      client_name: 'Ada Buyer',
      client_email: 'ada@example.com',
      invoice_id: null,
      mode: 'reservation',
      agreed_price: '10000000.00',
      reservation_threshold_percent: '20.00',
      reservation_amount: '2000000.00',
      installment_months: null,
      payment_window_expires_at: '2026-09-01T12:00:00Z',
      status: 'awaiting_approval',
      amount_paid: '0.00',
      reserved_at: null,
      completed_at: null,
      cancelled_at: null,
      created_by_id: 3,
      created_at: '2026-08-26T12:00:00Z',
      updated_at: '2026-08-26T12:00:00Z',
    })
    expect(purchase.mode).toBe('reservation')
    expect(purchase.status).toBe('awaiting_approval')
    expect(purchase.agreedPrice).toBe(10000000)
    expect(purchase.reservationAmount).toBe(2000000)
    expect(purchase.invoiceId).toBeNull()
  })
})
