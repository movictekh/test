import type { PaginatedQuotations, Quotation, RoleOption } from './quotation.types'

type R = Record<string, unknown>
const rec = (v: unknown): R =>
  typeof v === 'object' && v !== null && !Array.isArray(v) ? (v as R) : {}
const txt = (v: unknown, f = '') => (typeof v === 'string' ? v : f)
const num = (v: unknown, f = 0) => {
  const n = Number(v)
  return Number.isFinite(n) ? n : f
}
const nnum = (v: unknown) => (v == null || v === '' ? null : num(v))
const ntxt = (v: unknown) => (v == null || v === '' ? null : txt(v))
const displayName = (v: unknown) => {
  const r = rec(v)
  return (
    txt(r.name) ||
    txt(r.role_name) ||
    txt(r.full_name) ||
    [txt(r.first_name), txt(r.last_name)].filter(Boolean).join(' ') ||
    txt(r.email)
  )
}
function rows(payload: unknown) {
  if (Array.isArray(payload)) return { count: payload.length, rows: payload }
  const r = rec(payload)
  const items = Array.isArray(r.items)
    ? r.items
    : Array.isArray(r.results)
      ? r.results
      : Array.isArray(r.data)
        ? r.data
        : []
  return { count: num(r.count, items.length), rows: items }
}

export function mapQuotation(payload: unknown): Quotation {
  const v = rec(payload)
  const role = rec(v.required_approver_role)
  const approved = rec(v.approved_by)
  const created = rec(v.created_by)
  return {
    id: num(v.id),
    quoteNumber: txt(v.quote_number),
    clientId: num(v.client_id ?? rec(v.client).id),
    clientName: txt(v.client_name) || displayName(v.client),
    serviceId: num(v.service_id ?? rec(v.service).id),
    serviceName: txt(v.service_name) || displayName(v.service),
    serviceRequestId: nnum(v.service_request_id ?? rec(v.service_request).id),
    serviceRequestNumber:
      txt(v.service_request_number) || txt(rec(v.service_request).request_number),
    previousQuoteId: nnum(v.previous_quote_id ?? rec(v.previous_quote).id),
    previousQuoteNumber: txt(v.previous_quote_number) || txt(rec(v.previous_quote).quote_number),
    version: num(v.version, 1),
    requiredApproverRoleId: nnum(v.required_approver_role_id ?? role.id),
    requiredApproverRoleName:
      txt(v.required_approver_role_name) || displayName(v.required_approver_role),
    description: txt(v.description),
    scopeSummary: txt(v.scope_summary),
    terms: txt(v.terms),
    serviceFee: num(v.service_fee),
    otherCharges: num(v.other_charges),
    discount: num(v.discount),
    subtotal: num(v.subtotal),
    taxRate: num(v.tax_rate),
    taxAmount: num(v.tax_amount),
    depositPercent: num(v.deposit_percent),
    depositAmount: num(v.deposit_amount),
    amount: num(v.amount),
    validUntil: txt(v.valid_until),
    status: txt(v.status, 'draft') as Quotation['status'],
    statusDisplay: txt(v.status_display, txt(v.status)),
    approvedById: nnum(v.approved_by_id ?? approved.id),
    approvedByName: txt(v.approved_by_name) || displayName(v.approved_by),
    approvedAt: ntxt(v.approved_at),
    sentAt: ntxt(v.sent_at),
    clientRespondedAt: ntxt(v.client_responded_at),
    clientRejectionReason: txt(v.client_rejection_reason),
    createdById: nnum(v.created_by_id ?? created.id),
    createdByName: txt(v.created_by_name) || displayName(v.created_by),
    createdAt: txt(v.created_at),
    updatedAt: txt(v.updated_at),
  }
}

export function mapQuotationList(payload: unknown): PaginatedQuotations {
  const result = rows(payload)
  return { count: result.count, items: result.rows.map(mapQuotation) }
}

export function mapRoles(payload: unknown): RoleOption[] {
  return rows(payload)
    .rows.map((item) => {
      const r = rec(item)
      return { id: num(r.id), name: txt(r.name) || txt(r.role_name) }
    })
    .filter((item) => item.id > 0 && item.name.length > 0)
}
