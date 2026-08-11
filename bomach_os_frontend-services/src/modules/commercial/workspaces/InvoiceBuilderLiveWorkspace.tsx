import { IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useState } from 'react'

import { formatCurrency } from '@/shared/lib/formatters'

import type { Quotation } from '../quotation/quotation.types'
import type { CreateInvoiceFromQuoteInput } from '../billing/billing.types'
import { validateInvoiceDates } from '../billing/payment.validation'

function defaultDueDate() {
  const date = new Date()
  date.setDate(date.getDate() + 14)
  return date.toISOString().slice(0, 10)
}

export function InvoiceBuilderLiveWorkspace({
  quotation,
  eligibleQuotations,
  quotationSelectionLocked,
  quotationSelectionLoading,
  saving,
  onSelectQuotation,
  onClose,
  onSubmit,
}: {
  quotation: Quotation
  eligibleQuotations: Quotation[]
  quotationSelectionLocked: boolean
  quotationSelectionLoading: boolean
  saving: boolean
  onSelectQuotation: (quotationId: number) => void
  onClose: () => void
  onSubmit: (input: CreateInvoiceFromQuoteInput) => void
}) {
  const [errors, setErrors] = useState<Record<string, string>>({})

  const form = useForm({
    defaultValues: {
      dueDate: defaultDueDate(),
      paymentSchedule: 'Deposit / mobilisation',
      paymentInstructions:
        'Pay through client wallet, payment gateway, bank transfer or approved POS.',
      notes: quotation.terms || '',
    },
    onSubmit: ({ value }) => {
      const nextErrors: Record<string, string> = {}
      const dueDateError = validateInvoiceDates(value.dueDate)
      if (dueDateError) nextErrors.dueDate = dueDateError
      if (!value.paymentSchedule.trim()) {
        nextErrors.paymentSchedule = 'Payment schedule is required.'
      }
      setErrors(nextErrors)
      if (Object.keys(nextErrors).length > 0) return

      onSubmit({
        quoteId: quotation.id,
        dueDate: value.dueDate,
        paymentSchedule: value.paymentSchedule.trim(),
        paymentInstructions: value.paymentInstructions.trim(),
        notes: value.notes.trim(),
      })
    },
  })

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <form
        className="commercial-modal commercial-modal--xl"
        aria-label="Create Invoice / Payment Schedule"
        onMouseDown={(event) => event.stopPropagation()}
        onSubmit={(event) => {
          event.preventDefault()
          event.stopPropagation()
          void form.handleSubmit()
        }}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Create Invoice / Payment Schedule</h2>
            <p>Generate a draft invoice from an accepted quotation</p>
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
            <h3>Source quotation</h3>
            <div className="commercial-form-grid">
              <label className="commercial-field commercial-field--full">
                <span>Accepted quotation *</span>
                <select
                  value={quotation.id}
                  disabled={quotationSelectionLocked || quotationSelectionLoading}
                  onChange={(event) => onSelectQuotation(Number(event.target.value))}
                >
                  {eligibleQuotations.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.quoteNumber} — {item.clientName || `Client #${item.clientId}`} —{' '}
                      {formatCurrency(item.amount)}
                    </option>
                  ))}
                </select>
                {quotationSelectionLocked ? (
                  <small>This quotation was selected from the accepted Quote workflow.</small>
                ) : null}
              </label>
            </div>

            <div className="commercial-info-grid">
              <div>
                <div className="commercial-kl">Quote</div>
                <b>{quotation.quoteNumber}</b>
              </div>
              <div>
                <div className="commercial-kl">Client</div>
                <b>{quotation.clientName || `Client #${quotation.clientId}`}</b>
              </div>
              <div>
                <div className="commercial-kl">Service</div>
                <b>{quotation.serviceName}</b>
              </div>
              <div>
                <div className="commercial-kl">Accepted value</div>
                <b>{formatCurrency(quotation.amount)}</b>
              </div>
              <div>
                <div className="commercial-kl">Required deposit</div>
                <b>{formatCurrency(quotation.depositAmount)}</b>
              </div>
            </div>
          </section>

          <section className="commercial-form-section">
            <h3>Invoice details</h3>
            <div className="commercial-form-grid">
              <form.Field name="dueDate">
                {(field) => (
                  <label className="commercial-field">
                    <span>Due date *</span>
                    <input
                      type="date"
                      value={field.state.value}
                      onChange={(event) => {
                        if (errors.dueDate) {
                          setErrors((current) => ({
                            ...current,
                            dueDate: '',
                          }))
                        }
                        field.handleChange(event.target.value)
                      }}
                    />
                    {errors.dueDate ? (
                      <small className="commercial-field-error">{errors.dueDate}</small>
                    ) : null}
                  </label>
                )}
              </form.Field>

              <form.Field name="paymentSchedule">
                {(field) => (
                  <label className="commercial-field">
                    <span>Payment schedule *</span>
                    <input
                      value={field.state.value}
                      onChange={(event) => {
                        if (errors.paymentSchedule) {
                          setErrors((current) => ({
                            ...current,
                            paymentSchedule: '',
                          }))
                        }
                        field.handleChange(event.target.value)
                      }}
                    />
                    {errors.paymentSchedule ? (
                      <small className="commercial-field-error">{errors.paymentSchedule}</small>
                    ) : null}
                  </label>
                )}
              </form.Field>

              <form.Field name="paymentInstructions">
                {(field) => (
                  <label className="commercial-field commercial-field--full">
                    <span>Payment instructions</span>
                    <textarea
                      rows={3}
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                    />
                  </label>
                )}
              </form.Field>

              <form.Field name="notes">
                {(field) => (
                  <label className="commercial-field commercial-field--full">
                    <span>Notes</span>
                    <textarea
                      rows={3}
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                    />
                  </label>
                )}
              </form.Field>
            </div>
          </section>

          <section className="commercial-form-section commercial-quote-preview-section">
            <div className="commercial-form-section-heading">
              <div>
                <h3>Commercial amount</h3>
                <p>This invoice amount follows the approved quotation and is read-only here.</p>
              </div>
              <div className="commercial-quote-total-chip commercial-quote-total-chip--lg">
                <span>Accepted quote</span>
                <b>{formatCurrency(quotation.amount)}</b>
              </div>
            </div>
          </section>
        </div>

        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" disabled={saving} onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className="commercial-btn commercial-btn-primary"
            disabled={saving || quotationSelectionLoading}
          >
            {saving ? 'Creating...' : 'Create Draft Invoice'}
          </button>
        </footer>
      </form>
    </div>
  )
}
