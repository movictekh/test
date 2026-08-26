import { apiClient } from '@/shared/api/api-client'

import type {
  CreatePropertyPurchaseInput,
  ManualPurchaseClientInput,
  PropertyPurchase,
  PurchaseClient,
} from './real-estate.types'

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}
function text(value: unknown) {
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint')
    return String(value)
  return ''
}
function numberValue(value: unknown) {
  const parsed = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}
function nullableNumber(value: unknown) {
  if (value == null || value === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

export function mapPurchaseClient(value: unknown): PurchaseClient {
  const row = asRecord(value)
  return {
    id: numberValue(row.id),
    userId: numberValue(row.user_id),
    fullName: text(row.full_name),
    email: text(row.email),
    phone: text(row.phone),
    companyName: text(row.company_name),
  }
}

export function mapPropertyPurchase(value: unknown): PropertyPurchase {
  const row = asRecord(value)
  return {
    id: numberValue(row.id),
    propertyId: numberValue(row.property_id),
    propertyName: text(row.property_name),
    estateId: numberValue(row.estate_id),
    estateName: text(row.estate_name),
    clientId: numberValue(row.client_id),
    clientUserId: numberValue(row.client_user_id),
    clientName: text(row.client_name),
    clientEmail: text(row.client_email),
    invoiceId: nullableNumber(row.invoice_id),
    mode: text(row.mode) as PropertyPurchase['mode'],
    agreedPrice: numberValue(row.agreed_price),
    reservationThresholdPercent: nullableNumber(row.reservation_threshold_percent),
    reservationAmount: nullableNumber(row.reservation_amount),
    installmentMonths: nullableNumber(row.installment_months),
    paymentWindowExpiresAt: text(row.payment_window_expires_at) || null,
    status: text(row.status) as PropertyPurchase['status'],
    amountPaid: numberValue(row.amount_paid),
    reservedAt: text(row.reserved_at) || null,
    completedAt: text(row.completed_at) || null,
    cancelledAt: text(row.cancelled_at) || null,
    createdById: numberValue(row.created_by_id),
    createdAt: text(row.created_at),
    updatedAt: text(row.updated_at),
  }
}

export const propertyPurchaseApi = {
  searchClients: async (query: string) =>
    (
      await apiClient.get<unknown[]>(
        `/property-purchases/clients/search?q=${encodeURIComponent(query.trim())}`,
      )
    ).map(mapPurchaseClient),
  createClient: async (input: ManualPurchaseClientInput) =>
    mapPurchaseClient(
      await apiClient.post<unknown>('/property-purchases/clients', {
        email: input.email.trim(),
        first_name: input.firstName.trim(),
        last_name: input.lastName.trim(),
        phone_number: input.phoneNumber.trim() || null,
        company_name: input.companyName.trim() || null,
        send_portal_invite: input.sendPortalInvite,
      }),
    ),
  createPurchase: async (input: CreatePropertyPurchaseInput) =>
    mapPropertyPurchase(
      await apiClient.post<unknown>('/property-purchases/', {
        property_id: input.propertyId,
        client_id: input.clientId,
        mode: input.mode,
        agreed_price: input.agreedPrice,
        installment_months: input.installmentMonths,
      }),
    ),
}
