import { IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'

import { formatCurrency } from '@/shared/lib/formatters'
import { formatNumberFieldValue, parseNumberFieldValue } from '@/shared/lib/number-input'
import { Button } from '@/shared/ui/button'
import { EmptyState } from '@/shared/ui/empty-state'

import type { ServiceRequestDetail, ServiceRequestListItem } from '../api/service-requests.types'
import { quotationQueries } from '../quotation/quotation.queries'
import {
  calculateQuotationPreview,
  validateQuotationPricing,
} from '../quotation/quotation-pricing.utils'
import type {
  CreateQuotationInput,
  Quotation,
  UpdateQuotationInput,
} from '../quotation/quotation.types'

function defaultValidUntil() {
  const date = new Date()
  date.setDate(date.getDate() + 14)
  return date.toISOString().slice(0, 10)
}

type QuotationBuilderFieldName =
  | 'requestId'
  | 'description'
  | 'scopeSummary'
  | 'terms'
  | 'serviceFee'
  | 'otherCharges'
  | 'discount'
  | 'taxRate'
  | 'depositPercent'
  | 'validUntil'
  | 'requiredApproverRoleId'

function focusField(
  fieldRefs: React.MutableRefObject<Record<string, HTMLElement | null>>,
  fieldName: QuotationBuilderFieldName,
) {
  window.requestAnimationFrame(() => {
    const node = fieldRefs.current[fieldName]
    node?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    if (
      node instanceof HTMLInputElement ||
      node instanceof HTMLTextAreaElement ||
      node instanceof HTMLSelectElement
    ) {
      node.focus()
    }
  })
}

export function QuotationBuilderLiveWorkspace({
  mode,
  request,
  eligibleRequests,
  requestSelectionLocked = false,
  requestSelectionLoading = false,
  quote,
  saving,
  onClose,
  onRequestChange,
  onCreate,
  onUpdate,
}: {
  mode: 'create' | 'edit' | 'revision'
  request: ServiceRequestDetail
  eligibleRequests?: ServiceRequestListItem[]
  requestSelectionLocked?: boolean
  requestSelectionLoading?: boolean
  quote?: Quotation
  saving: boolean
  onClose: () => void
  onRequestChange?: (requestId: number) => void
  onCreate: (input: CreateQuotationInput) => void
  onUpdate: (input: UpdateQuotationInput) => void
}) {
  const rolesQuery = useQuery(quotationQueries.roles())
  const [fieldErrors, setFieldErrors] = useState<
    Partial<Record<QuotationBuilderFieldName, string>>
  >({})
  const fieldRefs = useRef<Record<string, HTMLElement | null>>({})

  const form = useForm({
    defaultValues: {
      description: quote?.description || `Quotation for ${request.serviceName}`,
      scopeSummary: quote?.scopeSummary || request.scopeSummary,
      terms:
        quote?.terms ||
        'Work begins after the required mobilisation payment and approved documents are received.',
      serviceFee: quote?.serviceFee || request.estimatedValue || request.budget || 0,
      otherCharges: quote?.otherCharges ?? 0,
      discount: quote?.discount ?? 0,
      taxRate: quote?.taxRate ?? 0,
      depositPercent: quote?.depositPercent ?? 30,
      validUntil: quote?.validUntil || defaultValidUntil(),
      requiredApproverRoleId: quote?.requiredApproverRoleId ?? 0,
    },
    onSubmit: ({ value }) => {
      const nextErrors: Partial<Record<QuotationBuilderFieldName, string>> = {
        ...validateQuotationPricing({
          serviceFee: Number(value.serviceFee),
          otherCharges: Number(value.otherCharges),
          discount: Number(value.discount),
          taxRate: Number(value.taxRate),
          depositPercent: Number(value.depositPercent),
        }),
      }

      if (!value.description.trim()) {
        nextErrors.description = 'Description is required.'
      }
      if (!value.scopeSummary.trim()) {
        nextErrors.scopeSummary = 'Scope of work is required.'
      }
      if (!value.terms.trim()) {
        nextErrors.terms = 'Commercial terms are required.'
      }
      if (!value.validUntil) {
        nextErrors.validUntil = 'Validity date is required.'
      }
      if (!value.requiredApproverRoleId) {
        nextErrors.requiredApproverRoleId = 'Select the required approver role.'
      }

      const firstErrorField = (
        [
          'requestId',
          'description',
          'scopeSummary',
          'validUntil',
          'serviceFee',
          'otherCharges',
          'discount',
          'taxRate',
          'depositPercent',
          'requiredApproverRoleId',
          'terms',
        ] as QuotationBuilderFieldName[]
      ).find((fieldName) => nextErrors[fieldName])

      if (firstErrorField) {
        setFieldErrors(nextErrors)
        focusField(fieldRefs, firstErrorField)
        return
      }

      setFieldErrors({})

      const payload = {
        description: value.description.trim(),
        scopeSummary: value.scopeSummary.trim(),
        terms: value.terms.trim(),
        serviceFee: Number(value.serviceFee),
        otherCharges: Number(value.otherCharges),
        discount: Number(value.discount),
        taxRate: Number(value.taxRate),
        depositPercent: Number(value.depositPercent),
        validUntil: value.validUntil,
        requiredApproverRoleId: value.requiredApproverRoleId,
      }

      if (mode === 'edit') {
        onUpdate(payload)
        return
      }

      onCreate({
        clientId: request.clientId,
        serviceId: request.serviceId,
        serviceRequestId: request.id,
        ...payload,
        ...(mode === 'revision' && quote ? { previousQuoteId: quote.id } : {}),
      })
    },
  })

  useEffect(() => {
    if (mode !== 'create') return
    form.setFieldValue('description', `Quotation for ${request.serviceName}`)
    form.setFieldValue('scopeSummary', request.scopeSummary)
    form.setFieldValue('serviceFee', request.estimatedValue || request.budget || 0)
    form.setFieldValue('otherCharges', 0)
    form.setFieldValue('discount', 0)
    form.setFieldValue('taxRate', 0)
    form.setFieldValue('depositPercent', 30)
    form.setFieldValue('requiredApproverRoleId', 0)
  }, [
    form,
    mode,
    request.budget,
    request.estimatedValue,
    request.scopeSummary,
    request.serviceName,
  ])

  const canSelectRequest =
    mode === 'create' &&
    !requestSelectionLocked &&
    Boolean(onRequestChange) &&
    (eligibleRequests?.length ?? 0) > 1

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <form
        className="commercial-modal commercial-modal--xl"
        aria-label="Build Quotation / Proposal"
        onMouseDown={(event) => event.stopPropagation()}
        onSubmit={(event) => {
          event.preventDefault()
          event.stopPropagation()
          void form.handleSubmit()
        }}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>
              {mode === 'revision'
                ? `Revise ${quote?.quoteNumber ?? 'Quotation'}`
                : mode === 'edit'
                  ? `Edit ${quote?.quoteNumber ?? 'Quotation'}`
                  : 'Build Quotation / Proposal'}
            </h2>
            <p>Scope, pricing, deposit and approval route</p>
          </div>
          <button
            type="button"
            className="commercial-modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            <IconX size={16} />
          </button>
        </header>

        <div className="commercial-modal-body">
          <section className="commercial-form-section">
            <div className="commercial-form-section-heading">
              <div>
                <h3>Source request</h3>
                <p>
                  {canSelectRequest
                    ? 'Choose the request this quotation should be built from.'
                    : 'This quotation is linked to the selected request.'}
                </p>
              </div>
            </div>

            {canSelectRequest ? (
              <div className="commercial-form-grid">
                <label className="commercial-field commercial-field--full">
                  <span>Service request *</span>
                  <select
                    ref={(node) => {
                      fieldRefs.current.requestId = node
                    }}
                    value={request.id}
                    disabled={requestSelectionLoading}
                    onChange={(event) => {
                      setFieldErrors((current) => {
                        if (!current.requestId) return current
                        const next = { ...current }
                        delete next.requestId
                        return next
                      })
                      onRequestChange?.(Number(event.target.value))
                    }}
                  >
                    {(eligibleRequests ?? []).map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.requestNumber} — {item.clientName} — {item.serviceName}
                      </option>
                    ))}
                  </select>
                  {fieldErrors.requestId ? (
                    <small className="commercial-field-error">{fieldErrors.requestId}</small>
                  ) : null}
                </label>
              </div>
            ) : null}

            <div className="commercial-info-grid">
              <div>
                <div className="commercial-kl">Request</div>
                <b>{request.requestNumber}</b>
              </div>
              <div>
                <div className="commercial-kl">Client</div>
                <b>{request.clientName}</b>
              </div>
              <div>
                <div className="commercial-kl">Service</div>
                <b>{request.serviceName}</b>
              </div>
              <div>
                <div className="commercial-kl">Branch</div>
                <b>{request.branchName || '—'}</b>
              </div>
            </div>
          </section>

          <section className="commercial-form-section">
            <h3>Offer</h3>
            <div className="commercial-form-grid">
              <form.Field name="description">
                {(field) => (
                  <label className="commercial-field commercial-field--full">
                    <span>Description *</span>
                    <input
                      ref={(node) => {
                        fieldRefs.current.description = node
                      }}
                      value={field.state.value}
                      onChange={(event) => {
                        setFieldErrors((current) => {
                          if (!current.description) return current
                          const next = { ...current }
                          delete next.description
                          return next
                        })
                        field.handleChange(event.target.value)
                      }}
                    />
                    {fieldErrors.description ? (
                      <small className="commercial-field-error">{fieldErrors.description}</small>
                    ) : null}
                  </label>
                )}
              </form.Field>

              <form.Field name="scopeSummary">
                {(field) => (
                  <label className="commercial-field commercial-field--full">
                    <span>Scope of work *</span>
                    <textarea
                      ref={(node) => {
                        fieldRefs.current.scopeSummary = node
                      }}
                      rows={4}
                      value={field.state.value}
                      onChange={(event) => {
                        setFieldErrors((current) => {
                          if (!current.scopeSummary) return current
                          const next = { ...current }
                          delete next.scopeSummary
                          return next
                        })
                        field.handleChange(event.target.value)
                      }}
                    />
                    {fieldErrors.scopeSummary ? (
                      <small className="commercial-field-error">{fieldErrors.scopeSummary}</small>
                    ) : null}
                  </label>
                )}
              </form.Field>

              <form.Field name="validUntil">
                {(field) => (
                  <label className="commercial-field">
                    <span>Valid until *</span>
                    <input
                      ref={(node) => {
                        fieldRefs.current.validUntil = node
                      }}
                      type="date"
                      value={field.state.value}
                      onChange={(event) => {
                        setFieldErrors((current) => {
                          if (!current.validUntil) return current
                          const next = { ...current }
                          delete next.validUntil
                          return next
                        })
                        field.handleChange(event.target.value)
                      }}
                    />
                    {fieldErrors.validUntil ? (
                      <small className="commercial-field-error">{fieldErrors.validUntil}</small>
                    ) : null}
                  </label>
                )}
              </form.Field>
            </div>
          </section>

          <section className="commercial-form-section">
            <h3>Pricing and approval</h3>
            <div className="commercial-form-grid">
              <form.Field name="serviceFee">
                {(field) => (
                  <label className="commercial-field">
                    <span>Service fee</span>
                    <input
                      ref={(node) => {
                        fieldRefs.current.serviceFee = node
                      }}
                      type="number"
                      min="0"
                      value={formatNumberFieldValue(field.state.value)}
                      onChange={(event) => {
                        setFieldErrors((current) => {
                          if (!current.serviceFee) return current
                          const next = { ...current }
                          delete next.serviceFee
                          return next
                        })
                        field.handleChange(parseNumberFieldValue(event.target.value))
                      }}
                    />
                    {fieldErrors.serviceFee ? (
                      <small className="commercial-field-error">{fieldErrors.serviceFee}</small>
                    ) : null}
                  </label>
                )}
              </form.Field>

              <form.Field name="otherCharges">
                {(field) => (
                  <label className="commercial-field">
                    <span>Other charges</span>
                    <input
                      ref={(node) => {
                        fieldRefs.current.otherCharges = node
                      }}
                      type="number"
                      min="0"
                      value={formatNumberFieldValue(field.state.value)}
                      onChange={(event) => {
                        setFieldErrors((current) => {
                          if (!current.otherCharges) return current
                          const next = { ...current }
                          delete next.otherCharges
                          return next
                        })
                        field.handleChange(parseNumberFieldValue(event.target.value))
                      }}
                    />
                    {fieldErrors.otherCharges ? (
                      <small className="commercial-field-error">{fieldErrors.otherCharges}</small>
                    ) : null}
                  </label>
                )}
              </form.Field>

              <form.Field name="discount">
                {(field) => (
                  <label className="commercial-field">
                    <span>Discount</span>
                    <input
                      ref={(node) => {
                        fieldRefs.current.discount = node
                      }}
                      type="number"
                      min="0"
                      value={formatNumberFieldValue(field.state.value)}
                      onChange={(event) => {
                        setFieldErrors((current) => {
                          if (!current.discount) return current
                          const next = { ...current }
                          delete next.discount
                          return next
                        })
                        field.handleChange(parseNumberFieldValue(event.target.value))
                      }}
                    />
                    {fieldErrors.discount ? (
                      <small className="commercial-field-error">{fieldErrors.discount}</small>
                    ) : null}
                  </label>
                )}
              </form.Field>

              <form.Field name="taxRate">
                {(field) => (
                  <label className="commercial-field">
                    <span>Tax (%)</span>
                    <input
                      ref={(node) => {
                        fieldRefs.current.taxRate = node
                      }}
                      type="number"
                      min="0"
                      max="100"
                      value={formatNumberFieldValue(field.state.value)}
                      onChange={(event) => {
                        setFieldErrors((current) => {
                          if (!current.taxRate) return current
                          const next = { ...current }
                          delete next.taxRate
                          return next
                        })
                        field.handleChange(parseNumberFieldValue(event.target.value))
                      }}
                    />
                    {fieldErrors.taxRate ? (
                      <small className="commercial-field-error">{fieldErrors.taxRate}</small>
                    ) : null}
                  </label>
                )}
              </form.Field>

              <form.Field name="depositPercent">
                {(field) => (
                  <label className="commercial-field">
                    <span>Required deposit (%)</span>
                    <input
                      ref={(node) => {
                        fieldRefs.current.depositPercent = node
                      }}
                      type="number"
                      min="0"
                      max="100"
                      value={formatNumberFieldValue(field.state.value)}
                      onChange={(event) => {
                        setFieldErrors((current) => {
                          if (!current.depositPercent) return current
                          const next = { ...current }
                          delete next.depositPercent
                          return next
                        })
                        field.handleChange(parseNumberFieldValue(event.target.value))
                      }}
                    />
                    {fieldErrors.depositPercent ? (
                      <small className="commercial-field-error">{fieldErrors.depositPercent}</small>
                    ) : null}
                  </label>
                )}
              </form.Field>

              {rolesQuery.isPending ? (
                <label className="commercial-field">
                  <span>Required approver role *</span>
                  <input value="Loading roles..." readOnly />
                </label>
              ) : rolesQuery.isError ? (
                <div className="commercial-field">
                  <span>Required approver role *</span>
                  <EmptyState
                    title="Approver roles unavailable"
                    description="Quotation submission is unavailable until approver roles are loaded."
                    action={
                      <Button variant="outline" size="sm" onClick={() => void rolesQuery.refetch()}>
                        Retry
                      </Button>
                    }
                  />
                </div>
              ) : (
                <form.Field name="requiredApproverRoleId">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Required approver role *</span>
                      <select
                        ref={(node) => {
                          fieldRefs.current.requiredApproverRoleId = node
                        }}
                        value={field.state.value}
                        onChange={(event) => {
                          setFieldErrors((current) => {
                            if (!current.requiredApproverRoleId) return current
                            const next = { ...current }
                            delete next.requiredApproverRoleId
                            return next
                          })
                          field.handleChange(Number(event.target.value))
                        }}
                      >
                        <option value={0}>Select role</option>
                        {rolesQuery.data.map((role) => (
                          <option key={role.id} value={role.id}>
                            {role.name}
                          </option>
                        ))}
                      </select>
                      {fieldErrors.requiredApproverRoleId ? (
                        <small className="commercial-field-error">
                          {fieldErrors.requiredApproverRoleId}
                        </small>
                      ) : null}
                    </label>
                  )}
                </form.Field>
              )}
            </div>
          </section>

          <section className="commercial-form-section">
            <h3>Commercial terms</h3>
            <form.Field name="terms">
              {(field) => (
                <label className="commercial-field commercial-field--full">
                  <span>Terms *</span>
                  <textarea
                    ref={(node) => {
                      fieldRefs.current.terms = node
                    }}
                    rows={3}
                    value={field.state.value}
                    onChange={(event) => {
                      setFieldErrors((current) => {
                        if (!current.terms) return current
                        const next = { ...current }
                        delete next.terms
                        return next
                      })
                      field.handleChange(event.target.value)
                    }}
                  />
                  {fieldErrors.terms ? (
                    <small className="commercial-field-error">{fieldErrors.terms}</small>
                  ) : null}
                </label>
              )}
            </form.Field>
          </section>

          <form.Subscribe
            selector={(state) => ({
              serviceFee: state.values.serviceFee,
              otherCharges: state.values.otherCharges,
              discount: state.values.discount,
              taxRate: state.values.taxRate,
              depositPercent: state.values.depositPercent,
            })}
          >
            {(value) => {
              const preview = calculateQuotationPreview({
                serviceFee: Number(value.serviceFee),
                otherCharges: Number(value.otherCharges),
                discount: Number(value.discount),
                taxRate: Number(value.taxRate),
                depositPercent: Number(value.depositPercent),
              })
              return (
                <section className="commercial-form-section commercial-quote-preview-section">
                  <div className="commercial-form-section-heading">
                    <div>
                      <h3>Quote total</h3>
                      <p>
                        Subtotal {formatCurrency(preview.subtotal)} · Discount{' '}
                        {formatCurrency(Number(value.discount))} · Tax{' '}
                        {formatCurrency(preview.taxAmount)} · Deposit{' '}
                        {formatCurrency(preview.depositAmount)}
                      </p>
                    </div>
                    <div className="commercial-quote-total-chip commercial-quote-total-chip--lg">
                      <span>Client price</span>
                      <b>{formatCurrency(preview.amount)}</b>
                    </div>
                  </div>
                </section>
              )
            }}
          </form.Subscribe>
        </div>

        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button
            type="submit"
            className="commercial-btn commercial-btn-primary"
            disabled={
              saving || rolesQuery.isPending || rolesQuery.isError || requestSelectionLoading
            }
          >
            {saving
              ? 'Saving...'
              : mode === 'edit'
                ? 'Save Changes'
                : mode === 'revision'
                  ? 'Submit Revision for Approval'
                  : 'Submit for Approval'}
          </button>
        </footer>
      </form>
    </div>
  )
}
