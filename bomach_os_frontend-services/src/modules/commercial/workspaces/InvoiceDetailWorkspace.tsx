import { IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useState } from 'react'

import { commercialMoney } from '../commercial.ui'
import type { CommercialInvoice, RecordPaymentInput } from '../types/commercial.types'
import { validatePaymentInput } from './commercial-finance.rules'

export function InvoiceDetailWorkspace({
  invoice,
  saving,
  onClose,
  onRecordPayment,
}: {
  invoice: CommercialInvoice
  saving: boolean
  onClose: () => void
  onRecordPayment: (input: RecordPaymentInput) => void
}) {
  const [errors, setErrors] = useState<Partial<Record<keyof RecordPaymentInput, string>>>({})

  const form = useForm({
    defaultValues: {
      invoiceId: invoice.id,
      amount: invoice.balance,
      method: 'Bank Transfer' as const,
      reference: '',
      paidAt: new Date().toISOString().slice(0, 10),
      note: '',
    } satisfies RecordPaymentInput,
  })

  const submit = () => {
    const value = form.state.values
    const nextErrors = validatePaymentInput(value, invoice)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length === 0) {
      onRecordPayment(value)
    }
  }

  return (
    <div className="commercial-modal-backdrop" onMouseDown={onClose}>
      <section
        className="commercial-modal commercial-modal--xl"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Invoice File — {invoice.id}</h2>
            <p>
              {invoice.client} · {invoice.service}
            </p>
          </div>
          <button type="button" className="commercial-modal-close" onClick={onClose}>
            <IconX size={16} />
          </button>
        </header>

        <div className="commercial-modal-body">
          <div className="commercial-g21">
            <div className="commercial-g21-main">
              <section className="commercial-form-section">
                <h3>Billing summary</h3>
                <div className="commercial-info-grid">
                  <div>
                    <div className="commercial-kl">Quotation</div>
                    <b>{invoice.quotationId}</b>
                  </div>
                  <div>
                    <div className="commercial-kl">Status</div>
                    <b>{invoice.status}</b>
                  </div>
                  <div>
                    <div className="commercial-kl">Total</div>
                    <b>{commercialMoney.format(invoice.total)}</b>
                  </div>
                  <div>
                    <div className="commercial-kl">Paid</div>
                    <b>{commercialMoney.format(invoice.amountPaid)}</b>
                  </div>
                  <div>
                    <div className="commercial-kl">Balance</div>
                    <b>{commercialMoney.format(invoice.balance)}</b>
                  </div>
                  <div>
                    <div className="commercial-kl">Due</div>
                    <b>{invoice.dueAt}</b>
                  </div>
                </div>
              </section>

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

            <aside className="commercial-g21-side">
              <form
                className="commercial-card commercial-request360-card"
                onSubmit={(event) => {
                  event.preventDefault()
                  submit()
                }}
              >
                <div className="commercial-card-header">
                  <div className="commercial-card-title-only">Record Payment</div>
                </div>

                <form.Field name="amount">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Amount</span>
                      <input
                        type="number"
                        min="0.01"
                        max={invoice.balance}
                        value={field.state.value}
                        onChange={(event) => field.handleChange(Number(event.target.value || 0))}
                      />
                      {errors.amount ? <em>{errors.amount}</em> : null}
                    </label>
                  )}
                </form.Field>

                <form.Field name="method">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Method</span>
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
                      <span>Reference</span>
                      <input
                        value={field.state.value}
                        onChange={(event) => field.handleChange(event.target.value)}
                      />
                      {errors.reference ? <em>{errors.reference}</em> : null}
                    </label>
                  )}
                </form.Field>

                <form.Field name="paidAt">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Payment date</span>
                      <input
                        type="date"
                        value={field.state.value}
                        onChange={(event) => field.handleChange(event.target.value)}
                      />
                    </label>
                  )}
                </form.Field>

                <form.Field name="note">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Note</span>
                      <textarea
                        rows={3}
                        value={field.state.value}
                        onChange={(event) => field.handleChange(event.target.value)}
                      />
                    </label>
                  )}
                </form.Field>

                <button
                  type="submit"
                  className="commercial-btn commercial-btn-primary commercial-btn-block"
                  disabled={saving || invoice.balance <= 0}
                >
                  {saving ? 'Recording...' : 'Record Payment'}
                </button>
              </form>
            </aside>
          </div>
        </div>

        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" onClick={onClose}>
            Close
          </button>
        </footer>
      </section>
    </div>
  )
}
