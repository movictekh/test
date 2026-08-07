import { IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useState } from 'react'

import { formatNumberFieldValue, parseNumberFieldValue } from '@/shared/lib/number-input'

import { commercialMoney, invoiceStatusClass } from '../commercial.ui'
import type { CommercialInvoice, RecordPaymentInput } from '../types/commercial.types'
import { validatePaymentInput } from './commercial-finance.rules'

export function InvoiceDetailWorkspace({
  invoice,
  saving,
  onClose,
  canConfirmPayment,
  onRecordPayment,
}: {
  invoice: CommercialInvoice
  saving: boolean
  onClose: () => void
  canConfirmPayment: boolean
  onRecordPayment: (input: RecordPaymentInput) => void
}) {
  const [errors, setErrors] = useState<Partial<Record<keyof RecordPaymentInput, string>>>({})

  const defaultValues: RecordPaymentInput = {
    invoiceId: invoice.id,
    amount: invoice.balance,
    method: 'Bank Transfer',
    reference: '',
    paidAt: new Date().toISOString().slice(0, 10),
    note: '',
  }

  const form = useForm({ defaultValues })

  const submit = () => {
    const value = form.state.values
    const nextErrors = validatePaymentInput(value, invoice)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length === 0) {
      onRecordPayment(value)
    }
  }

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="commercial-modal commercial-modal--xl"
        role="dialog"
        aria-modal="true"
        aria-label={`Invoice ${invoice.id}`}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Invoice {invoice.id}</h2>
            <p>
              {invoice.quotationId} · {invoice.schedule}
            </p>
          </div>
          <div className="commercial-modal-header-meta">
            <span className={`commercial-pill ${invoiceStatusClass(invoice.status)}`}>
              {invoice.status}
            </span>
            <button
              type="button"
              className="commercial-modal-close"
              onClick={onClose}
              aria-label="Close"
            >
              <IconX size={16} />
            </button>
          </div>
        </header>

        <div className="commercial-modal-body">
          <section className="commercial-form-section">
            <h3>Billing summary</h3>
            <div className="commercial-quote-pricing-layout">
              <div className="commercial-info-grid">
                <div>
                  <div className="commercial-kl">Client</div>
                  <b>{invoice.client}</b>
                </div>
                <div>
                  <div className="commercial-kl">Service</div>
                  <b>{invoice.service}</b>
                </div>
                <div>
                  <div className="commercial-kl">Quotation</div>
                  <b>{invoice.quotationId}</b>
                </div>
                <div>
                  <div className="commercial-kl">Due date</div>
                  <b>{invoice.dueAt}</b>
                </div>
                <div className="commercial-info-full">
                  <div className="commercial-kl">Payment instructions</div>
                  <p>{invoice.paymentInstructions}</p>
                </div>
              </div>
              <article className="commercial-quote-value-card">
                <div className="commercial-kpi-label">Outstanding balance</div>
                <div className="commercial-kpi-value">
                  {commercialMoney.format(invoice.balance)}
                </div>
                <div className="commercial-kpi-note">
                  Paid {commercialMoney.format(invoice.amountPaid)} of{' '}
                  {commercialMoney.format(invoice.total)}
                </div>
              </article>
            </div>
          </section>

          {invoice.balance > 0 && canConfirmPayment ? (
            <section className="commercial-form-section">
              <h3>Record payment</h3>
              <p className="commercial-form-note">
                Confirm a receipt against the outstanding balance
              </p>
              <div className="commercial-form-grid">
                <form.Field name="amount">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Payment amount *</span>
                      <input
                        type="number"
                        min="0.01"
                        max={invoice.balance}
                        value={formatNumberFieldValue(field.state.value)}
                        onChange={(event) =>
                          field.handleChange(parseNumberFieldValue(event.target.value))
                        }
                      />
                      {errors.amount ? <em>{errors.amount}</em> : null}
                    </label>
                  )}
                </form.Field>

                <form.Field name="method">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Method *</span>
                      <select
                        value={field.state.value}
                        onChange={(event) =>
                          field.handleChange(event.target.value as typeof field.state.value)
                        }
                      >
                        {['Bank Transfer', 'Card', 'Cash', 'POS', 'Cheque'].map((method) => (
                          <option key={method}>{method}</option>
                        ))}
                      </select>
                    </label>
                  )}
                </form.Field>

                <form.Field name="reference">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Reference *</span>
                      <input
                        value={field.state.value}
                        onChange={(event) => field.handleChange(event.target.value)}
                        placeholder="Transfer / receipt reference"
                      />
                      {errors.reference ? <em>{errors.reference}</em> : null}
                    </label>
                  )}
                </form.Field>

                <form.Field name="paidAt">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Payment date *</span>
                      <input
                        type="date"
                        value={field.state.value}
                        onChange={(event) => field.handleChange(event.target.value)}
                      />
                      {errors.paidAt ? <em>{errors.paidAt}</em> : null}
                    </label>
                  )}
                </form.Field>

                <form.Field name="note">
                  {(field) => (
                    <label className="commercial-field commercial-field--full">
                      <span>Note</span>
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
          ) : null}

          <section className="commercial-form-section">
            <h3>Payment history</h3>
            <div className="commercial-timeline-list">
              {[...invoice.payments].reverse().map((payment) => (
                <article className="commercial-tl" key={payment.id}>
                  <b>
                    {commercialMoney.format(payment.amount)} · {payment.method}
                  </b>
                  <p>
                    {payment.reference}
                    {payment.note ? ` · ${payment.note}` : ''}
                    <br />
                    <strong>{payment.recordedBy}</strong>
                  </p>
                  <time>{payment.paidAt}</time>
                </article>
              ))}
              {invoice.payments.length === 0 ? (
                <div className="commercial-empty">No payment has been recorded.</div>
              ) : null}
            </div>
          </section>
        </div>

        <footer className="commercial-modal-footer">
          <div className="commercial-modal-footer-start">
            <button type="button" className="commercial-btn" onClick={onClose}>
              Close
            </button>
          </div>
          <div className="commercial-modal-footer-actions">
            {invoice.balance > 0 && canConfirmPayment ? (
              <button
                type="button"
                className="commercial-btn commercial-btn-green"
                disabled={saving}
                onClick={submit}
              >
                {saving ? 'Recording...' : 'Confirm Payment'}
              </button>
            ) : null}
          </div>
        </footer>
      </section>
    </div>
  )
}
