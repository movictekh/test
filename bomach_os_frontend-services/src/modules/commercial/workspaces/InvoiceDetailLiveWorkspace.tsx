import { IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useState } from 'react'

import { formatNumberFieldValue, parseNumberFieldValue } from '@/shared/lib/number-input'

import { getInvoiceCapabilities } from '../billing/invoice-capabilities'
import {
  paymentMethodOptions,
  type Invoice,
  type Payment,
  type RecordPaymentInput,
  type UpdateInvoiceInput,
} from '../billing/billing.types'
import { validateInvoiceDates, validatePaymentInput } from '../billing/payment.validation'

function paymentMethodLabel(method: string) {
  return paymentMethodOptions.find((item) => item.value === method)?.label ?? method
}

function formatPreciseCurrency(value: number) {
  const amount = Number(value) || 0
  const hasFraction = Math.abs(amount % 1) > 0.000001

  return `₦${new Intl.NumberFormat('en-NG', {
    minimumFractionDigits: hasFraction ? 2 : 0,
    maximumFractionDigits: 2,
  }).format(amount)}`
}

function statusClass(status: Invoice['status']) {
  if (status === 'paid') return 'commercial-pill-green'
  if (status === 'overdue' || status === 'cancelled') {
    return 'commercial-pill-gray'
  }
  if (status === 'partially_paid') return 'commercial-pill-yellow'
  return 'commercial-pill-blue'
}

export function InvoiceDetailLiveWorkspace({
  invoice,
  payments,
  paymentsLoading,
  paymentsError,
  canViewPayments,
  onRetryPayments,
  saving,
  canUpdate,
  canRecordPayment,
  canCreateServiceOrder,
  canViewServiceOrder,
  onClose,
  onCreateServiceOrder,
  onOpenServiceOrder,
  onUpdate,
  onSend,
  onCancel,
  onRecordPayment,
}: {
  invoice: Invoice
  payments: Payment[]
  paymentsLoading: boolean
  paymentsError: string
  canViewPayments: boolean
  onRetryPayments: () => void
  saving: boolean
  canUpdate: boolean
  canRecordPayment: boolean
  canCreateServiceOrder: boolean
  canViewServiceOrder: boolean
  onClose: () => void
  onCreateServiceOrder: () => void
  onOpenServiceOrder: () => void
  onUpdate: (input: UpdateInvoiceInput) => void
  onSend: () => void
  onCancel: () => void
  onRecordPayment: (input: Omit<RecordPaymentInput, 'createdById'>) => void
}) {
  const capabilities = getInvoiceCapabilities(invoice)
  const [editing, setEditing] = useState(false)
  const [paymentErrors, setPaymentErrors] = useState<Record<string, string>>({})
  const [editErrors, setEditErrors] = useState<Record<string, string>>({})

  const editForm = useForm({
    defaultValues: {
      dueDate: invoice.dueDate,
      paymentSchedule: invoice.paymentSchedule,
      paymentInstructions: invoice.paymentInstructions,
      notes: invoice.notes,
    },
    onSubmit: ({ value }) => {
      const nextErrors: Record<string, string> = {}
      const dueDateError = validateInvoiceDates(value.dueDate)
      if (dueDateError) nextErrors.dueDate = dueDateError
      if (!value.paymentSchedule.trim()) {
        nextErrors.paymentSchedule = 'Payment schedule is required.'
      }
      setEditErrors(nextErrors)
      if (Object.keys(nextErrors).length > 0) return

      onUpdate({
        dueDate: value.dueDate,
        paymentSchedule: value.paymentSchedule.trim(),
        paymentInstructions: value.paymentInstructions.trim(),
        notes: value.notes.trim(),
      })
    },
  })

  const paymentForm = useForm({
    defaultValues: {
      invoiceId: invoice.id,
      amount: invoice.balance,
      paymentMethod: 'bank_transfer' as const,
      paymentDate: new Date().toISOString().slice(0, 10),
      transactionReference: '',
      notes: '',
    },
    onSubmit: ({ value }) => {
      const nextErrors = validatePaymentInput(value, invoice)
      setPaymentErrors(nextErrors)
      if (Object.keys(nextErrors).length > 0) return
      onRecordPayment(value)
    },
  })

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="commercial-modal commercial-modal--xl"
        role="dialog"
        aria-modal="true"
        aria-label={`Invoice ${invoice.invoiceNumber}`}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Invoice {invoice.invoiceNumber}</h2>
            <p>
              {invoice.serviceName} · {invoice.paymentSchedule || 'Payment schedule'}
            </p>
          </div>
          <div className="commercial-modal-header-meta">
            <span className={`commercial-pill ${statusClass(invoice.status)}`}>
              {invoice.status.replaceAll('_', ' ')}
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
                  <b>{invoice.clientName || `Client #${invoice.clientId}`}</b>
                </div>
                <div>
                  <div className="commercial-kl">Service</div>
                  <b>{invoice.serviceName}</b>
                </div>
                <div>
                  <div className="commercial-kl">Quote</div>
                  <b>{invoice.quoteId ? `#${invoice.quoteId}` : '—'}</b>
                </div>
                <div>
                  <div className="commercial-kl">Issue date</div>
                  <b>{invoice.issueDate}</b>
                </div>
                <div>
                  <div className="commercial-kl">Due date</div>
                  <b>{invoice.dueDate}</b>
                </div>
                <div>
                  <div className="commercial-kl">Payment threshold</div>
                  <b>{formatPreciseCurrency(invoice.activationThresholdAmount)}</b>
                </div>
                <div className="commercial-info-full">
                  <div className="commercial-kl">Payment instructions</div>
                  <p>{invoice.paymentInstructions || '—'}</p>
                </div>
              </div>

              <article className="commercial-quote-value-card">
                <div className="commercial-kpi-label">Outstanding balance</div>
                <div className="commercial-kpi-value">{formatPreciseCurrency(invoice.balance)}</div>
                <div className="commercial-kpi-note">
                  Paid {formatPreciseCurrency(invoice.amountPaid)} of{' '}
                  {formatPreciseCurrency(invoice.totalAmount)}
                </div>
              </article>
            </div>
          </section>

          <section className="commercial-form-section">
            <h3>Pricing breakdown</h3>
            <div className="commercial-quote-breakdown">
              <div>
                <span>Subtotal</span>
                <b>{formatPreciseCurrency(invoice.subtotal)}</b>
              </div>
              <div>
                <span>Tax ({invoice.taxRate}%)</span>
                <b>{formatPreciseCurrency(invoice.taxAmount)}</b>
              </div>
              <div className="commercial-quote-breakdown-total">
                <span>Total</span>
                <b>{formatPreciseCurrency(invoice.totalAmount)}</b>
              </div>
              <div>
                <span>Paid</span>
                <b>{formatPreciseCurrency(invoice.amountPaid)}</b>
              </div>
              <div>
                <span>Balance</span>
                <b>{formatPreciseCurrency(invoice.balance)}</b>
              </div>
            </div>
          </section>

          {invoice.activationThresholdMetAt ? (
            <section className="commercial-form-section">
              <div className="commercial-notice commercial-notice-blue">
                Required mobilisation/payment threshold was met on{' '}
                {new Date(invoice.activationThresholdMetAt).toLocaleString('en-GB')}. This invoice
                is ready for the Service Order stage.
              </div>
            </section>
          ) : null}

          {editing ? (
            <form
              className="commercial-form-section"
              onSubmit={(event) => {
                event.preventDefault()
                void editForm.handleSubmit()
              }}
            >
              <h3>Edit invoice controls</h3>
              <p className="commercial-form-note">
                Accepted Quote pricing is kept read-only. Only billing controls are editable.
              </p>
              <div className="commercial-form-grid">
                <editForm.Field name="dueDate">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Due date *</span>
                      <input
                        type="date"
                        value={field.state.value}
                        onChange={(event) => field.handleChange(event.target.value)}
                      />
                      {editErrors.dueDate ? (
                        <small className="commercial-field-error">{editErrors.dueDate}</small>
                      ) : null}
                    </label>
                  )}
                </editForm.Field>

                <editForm.Field name="paymentSchedule">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Payment schedule *</span>
                      <input
                        value={field.state.value}
                        onChange={(event) => field.handleChange(event.target.value)}
                      />
                      {editErrors.paymentSchedule ? (
                        <small className="commercial-field-error">
                          {editErrors.paymentSchedule}
                        </small>
                      ) : null}
                    </label>
                  )}
                </editForm.Field>

                <editForm.Field name="paymentInstructions">
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
                </editForm.Field>

                <editForm.Field name="notes">
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
                </editForm.Field>
              </div>
              <div className="commercial-modal-footer-actions">
                <button
                  type="button"
                  className="commercial-btn"
                  disabled={saving}
                  onClick={() => setEditing(false)}
                >
                  Cancel edit
                </button>
                <button
                  type="submit"
                  className="commercial-btn commercial-btn-primary"
                  disabled={saving}
                >
                  {saving ? 'Saving...' : 'Save changes'}
                </button>
              </div>
            </form>
          ) : null}

          {capabilities.recordPayment && canRecordPayment ? (
            <form
              className="commercial-form-section"
              onSubmit={(event) => {
                event.preventDefault()
                void paymentForm.handleSubmit()
              }}
            >
              <h3>Record confirmed payment</h3>
              <p className="commercial-form-note">
                Use this only for a payment that has already been verified. Client-submitted proofs
                are reviewed from Payment Submissions.
              </p>
              <div className="commercial-form-grid">
                <paymentForm.Field name="amount">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Payment amount *</span>
                      <input
                        type="number"
                        min="0.01"
                        step="0.01"
                        max={invoice.balance}
                        value={formatNumberFieldValue(field.state.value)}
                        onChange={(event) =>
                          field.handleChange(parseNumberFieldValue(event.target.value))
                        }
                      />
                      {paymentErrors.amount ? (
                        <small className="commercial-field-error">{paymentErrors.amount}</small>
                      ) : null}
                    </label>
                  )}
                </paymentForm.Field>

                <paymentForm.Field name="paymentMethod">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Payment method *</span>
                      <select
                        value={field.state.value}
                        onChange={(event) =>
                          field.handleChange(event.target.value as typeof field.state.value)
                        }
                      >
                        {paymentMethodOptions.map((method) => (
                          <option key={method.value} value={method.value}>
                            {method.label}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                </paymentForm.Field>

                <paymentForm.Field name="transactionReference">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Transaction reference *</span>
                      <input
                        value={field.state.value}
                        onChange={(event) => field.handleChange(event.target.value)}
                        placeholder="Bank / gateway / receipt reference"
                      />
                      {paymentErrors.transactionReference ? (
                        <small className="commercial-field-error">
                          {paymentErrors.transactionReference}
                        </small>
                      ) : null}
                    </label>
                  )}
                </paymentForm.Field>

                <paymentForm.Field name="paymentDate">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Payment date *</span>
                      <input
                        type="date"
                        value={field.state.value}
                        onChange={(event) => field.handleChange(event.target.value)}
                      />
                    </label>
                  )}
                </paymentForm.Field>

                <paymentForm.Field name="notes">
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
                </paymentForm.Field>
              </div>
              <div className="commercial-modal-footer-actions">
                <button
                  type="submit"
                  className="commercial-btn commercial-btn-green"
                  disabled={saving}
                >
                  {saving ? 'Recording...' : 'Confirm Payment'}
                </button>
              </div>
            </form>
          ) : null}

          <section className="commercial-form-section">
            <h3>Payment history</h3>
            {!canViewPayments ? (
              <div className="commercial-empty">
                You do not have permission to view payment history.
              </div>
            ) : paymentsLoading ? (
              <div className="commercial-empty">Loading payments...</div>
            ) : paymentsError ? (
              <div className="commercial-empty">
                <p>{paymentsError}</p>
                <button
                  type="button"
                  className="commercial-btn commercial-btn-small"
                  onClick={onRetryPayments}
                >
                  Retry
                </button>
              </div>
            ) : payments.length === 0 ? (
              <div className="commercial-empty">No confirmed payment has been recorded.</div>
            ) : (
              <div className="commercial-timeline-list">
                {payments.map((payment) => (
                  <article className="commercial-tl" key={payment.id}>
                    <b>
                      {formatPreciseCurrency(payment.amount)} ·{' '}
                      {paymentMethodLabel(payment.paymentMethod)}
                    </b>
                    <p>
                      {payment.paymentReference}
                      {payment.transactionReference ? ` · ${payment.transactionReference}` : ''}
                      {payment.notes ? ` · ${payment.notes}` : ''}
                    </p>
                    <time>{payment.paymentDate}</time>
                  </article>
                ))}
              </div>
            )}
          </section>

          {invoice.items.length > 0 ? (
            <section className="commercial-form-section">
              <h3>Invoice items</h3>
              <div className="commercial-table-wrap commercial-table-wrap--fit">
                <table className="commercial-table commercial-table--fit">
                  <thead>
                    <tr>
                      <th>Description</th>
                      <th>Quantity</th>
                      <th>Unit price</th>
                      <th>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoice.items.map((item) => (
                      <tr key={item.id}>
                        <td>{item.description}</td>
                        <td>{item.quantity}</td>
                        <td>{formatPreciseCurrency(item.unitPrice)}</td>
                        <td>{formatPreciseCurrency(item.total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}
        </div>

        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" onClick={onClose}>
            Close
          </button>
          <div className="commercial-modal-footer-actions">
            {invoice.activationThresholdMetAt && !invoice.orderId && canCreateServiceOrder ? (
              <button
                type="button"
                className="commercial-btn commercial-btn-green"
                disabled={saving}
                onClick={onCreateServiceOrder}
              >
                Create Service Order
              </button>
            ) : null}

            {invoice.orderId && canViewServiceOrder ? (
              <button
                type="button"
                className="commercial-btn commercial-btn-primary"
                disabled={saving}
                onClick={onOpenServiceOrder}
              >
                Open Service Order
              </button>
            ) : null}

            {capabilities.edit && canUpdate && !editing ? (
              <button
                type="button"
                className="commercial-btn"
                disabled={saving}
                onClick={() => setEditing(true)}
              >
                Edit Invoice
              </button>
            ) : null}

            {capabilities.cancel && canUpdate ? (
              <button type="button" className="commercial-btn" disabled={saving} onClick={onCancel}>
                Cancel Invoice
              </button>
            ) : null}

            {capabilities.send && canUpdate ? (
              <button
                type="button"
                className="commercial-btn commercial-btn-primary"
                disabled={saving}
                onClick={onSend}
              >
                {invoice.status === 'sent' ? 'Resend Invoice' : 'Send Invoice'}
              </button>
            ) : null}
          </div>
        </footer>
      </section>
    </div>
  )
}
