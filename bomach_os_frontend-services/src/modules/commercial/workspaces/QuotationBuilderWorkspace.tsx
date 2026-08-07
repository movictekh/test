import { IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'

import { formatNumberFieldValue, parseNumberFieldValue } from '@/shared/lib/number-input'
import { commercialMoney, quotationApprovers } from '../commercial.ui'
import type { CommercialServiceRequest, CreateQuotationInput } from '../types/commercial.types'
import { getQuotationEligibleRequests, validateQuotationDraft } from './quotation-workflow.rules'

function defaultValidUntil() {
  const date = new Date()
  date.setDate(date.getDate() + 14)
  return date.toISOString().slice(0, 10)
}

export function QuotationBuilderWorkspace({
  requests,
  initialRequestId,
  saving,
  onClose,
  onSubmit,
}: {
  requests: CommercialServiceRequest[]
  initialRequestId?: string
  saving: boolean
  onClose: () => void
  onSubmit: (input: CreateQuotationInput) => void
}) {
  const eligibleRequests = getQuotationEligibleRequests(requests)
  const source =
    eligibleRequests.find((item) => item.id === initialRequestId) ?? eligibleRequests[0] ?? null

  const defaultValues: {
    requestId: string
    validUntil: string
    scopeSummary: string
    serviceFee: number
    otherCharges: number
    discount: number
    taxPercent: number
    depositPercent: number
    approvalRoute: string
    paymentTerms: string
  } = {
    requestId: source?.id ?? '',
    validUntil: defaultValidUntil(),
    scopeSummary: source?.details ?? '',
    serviceFee: source?.estimate || source?.budget || 0,
    otherCharges: 0,
    discount: 0,
    taxPercent: 0,
    depositPercent: 30,
    approvalRoute: quotationApprovers[0],
    paymentTerms:
      'Work begins after the required mobilisation payment and approved documents are received.',
  }

  const form = useForm({ defaultValues })

  const submitWithStatus = (status: CreateQuotationInput['status']) => {
    const value = form.state.values
    const errors = validateQuotationDraft(value)
    if (Object.keys(errors).length > 0) {
      const message = Object.values(errors)[0]
      if (message) window.alert(message)
      return
    }
    onSubmit({
      requestId: value.requestId,
      validUntil: value.validUntil,
      scopeSummary: value.scopeSummary.trim(),
      serviceFee: Number(value.serviceFee) || 0,
      otherCharges: Number(value.otherCharges) || 0,
      discount: Number(value.discount) || 0,
      taxPercent: Number(value.taxPercent) || 0,
      depositPercent: Number(value.depositPercent) || 0,
      approvalRoute: value.approvalRoute,
      paymentTerms: value.paymentTerms.trim(),
      status,
    })
  }

  const applyRequest = (requestId: string) => {
    const next = requests.find((item) => item.id === requestId)
    form.setFieldValue('requestId', requestId)
    form.setFieldValue('scopeSummary', next?.details ?? '')
    form.setFieldValue('serviceFee', next?.estimate || next?.budget || 0)
  }

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <form
        className="commercial-modal commercial-modal--xl"
        aria-label="Build Quotation / Proposal"
        onSubmit={(event) => {
          event.preventDefault()
          submitWithStatus('Draft')
        }}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Build Quotation / Proposal</h2>
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
            <h3>Source request</h3>
            <div className="commercial-form-grid">
              <form.Field name="requestId">
                {(field) => (
                  <label className="commercial-field">
                    <span>Service request *</span>
                    <select
                      value={field.state.value}
                      onChange={(event) => applyRequest(event.target.value)}
                    >
                      {eligibleRequests.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.id} — {item.client} — {item.service}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </form.Field>

              <form.Field name="validUntil">
                {(field) => (
                  <label className="commercial-field">
                    <span>Valid until *</span>
                    <input
                      type="date"
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                    />
                  </label>
                )}
              </form.Field>
            </div>
          </section>

          <section className="commercial-form-section">
            <h3>Scope summary</h3>
            <form.Field name="scopeSummary">
              {(field) => (
                <label className="commercial-field commercial-field--full">
                  <span>Offer scope</span>
                  <textarea
                    rows={4}
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                  />
                </label>
              )}
            </form.Field>
          </section>

          <section className="commercial-form-section">
            <h3>Pricing and approval</h3>
            <div className="commercial-form-grid">
              <form.Field name="serviceFee">
                {(field) => (
                  <label className="commercial-field">
                    <span>Service fee</span>
                    <input
                      type="number"
                      min="0"
                      value={formatNumberFieldValue(field.state.value)}
                      onChange={(event) =>
                        field.handleChange(parseNumberFieldValue(event.target.value))
                      }
                    />
                  </label>
                )}
              </form.Field>

              <form.Field name="otherCharges">
                {(field) => (
                  <label className="commercial-field">
                    <span>Other charges</span>
                    <input
                      type="number"
                      min="0"
                      value={formatNumberFieldValue(field.state.value)}
                      onChange={(event) =>
                        field.handleChange(parseNumberFieldValue(event.target.value))
                      }
                    />
                  </label>
                )}
              </form.Field>

              <form.Field name="discount">
                {(field) => (
                  <label className="commercial-field">
                    <span>Discount</span>
                    <input
                      type="number"
                      min="0"
                      value={formatNumberFieldValue(field.state.value)}
                      onChange={(event) =>
                        field.handleChange(parseNumberFieldValue(event.target.value))
                      }
                    />
                  </label>
                )}
              </form.Field>

              <form.Field name="taxPercent">
                {(field) => (
                  <label className="commercial-field">
                    <span>Tax (%)</span>
                    <input
                      type="number"
                      min="0"
                      value={formatNumberFieldValue(field.state.value)}
                      onChange={(event) =>
                        field.handleChange(parseNumberFieldValue(event.target.value))
                      }
                    />
                  </label>
                )}
              </form.Field>

              <form.Field name="depositPercent">
                {(field) => (
                  <label className="commercial-field">
                    <span>Required deposit (%)</span>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={formatNumberFieldValue(field.state.value)}
                      onChange={(event) =>
                        field.handleChange(parseNumberFieldValue(event.target.value))
                      }
                    />
                  </label>
                )}
              </form.Field>

              <form.Field name="approvalRoute">
                {(field) => (
                  <label className="commercial-field">
                    <span>Approval route</span>
                    <select
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                    >
                      {quotationApprovers.map((approver) => (
                        <option key={approver}>{approver}</option>
                      ))}
                    </select>
                  </label>
                )}
              </form.Field>
            </div>
          </section>

          <section className="commercial-form-section">
            <h3>Payment schedule & terms</h3>
            <form.Field name="paymentTerms">
              {(field) => (
                <label className="commercial-field commercial-field--full">
                  <span>Terms</span>
                  <textarea
                    rows={3}
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                  />
                </label>
              )}
            </form.Field>
          </section>

          <form.Subscribe
            selector={(state) => ({
              serviceFee: state.values.serviceFee,
              otherCharges: state.values.otherCharges,
              discount: state.values.discount,
              taxPercent: state.values.taxPercent,
              depositPercent: state.values.depositPercent,
            })}
          >
            {(values) => {
              const subtotal = Number(values.serviceFee) + Number(values.otherCharges)
              const discount = Number(values.discount) || 0
              const tax = ((subtotal - discount) * Number(values.taxPercent)) / 100
              const total = subtotal - discount + tax
              const deposit = (total * Number(values.depositPercent)) / 100

              return (
                <section className="commercial-form-section commercial-quote-preview-section">
                  <div className="commercial-form-section-heading">
                    <div>
                      <h3>Quote total</h3>
                      <p>
                        Subtotal {commercialMoney.format(subtotal)} · Discount{' '}
                        {commercialMoney.format(discount)} · Tax {commercialMoney.format(tax)} ·
                        Deposit {commercialMoney.format(deposit)}
                      </p>
                    </div>
                    <div className="commercial-quote-total-chip commercial-quote-total-chip--lg">
                      <span>Client price</span>
                      <b>{commercialMoney.format(total)}</b>
                    </div>
                  </div>
                </section>
              )
            }}
          </form.Subscribe>
        </div>

        <footer className="commercial-modal-footer">
          <div className="commercial-modal-footer-start">
            <button type="button" className="commercial-btn" onClick={onClose} disabled={saving}>
              Cancel
            </button>
          </div>
          <div className="commercial-modal-footer-actions">
            <button
              type="button"
              className="commercial-btn"
              disabled={saving || eligibleRequests.length === 0}
              onClick={() => submitWithStatus('Draft')}
            >
              {saving ? 'Saving...' : 'Save Draft'}
            </button>
            <button
              type="button"
              className="commercial-btn commercial-btn-primary"
              disabled={saving || eligibleRequests.length === 0}
              onClick={() => submitWithStatus('Awaiting Approval')}
            >
              {saving ? 'Submitting...' : 'Submit for Approval'}
            </button>
          </div>
        </footer>
      </form>
    </div>
  )
}
