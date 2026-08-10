import { IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useState } from 'react'

import { formatCurrency } from '@/shared/lib/formatters'
import type { Invoice } from '@/modules/commercial/billing/billing.types'

import { validateOrderCreation } from '../service-orders/service-order.validation'
import type {
  CreateServiceOrderFromInvoiceInput,
  EmployeeOption,
} from '../service-orders/service-order.types'

export function CreateServiceOrderLiveWorkspace({
  invoice,
  eligibleInvoices,
  employees,
  invoiceSelectionLocked,
  invoiceSelectionLoading,
  saving,
  onSelectInvoice,
  onClose,
  onSubmit,
}: {
  invoice: Invoice
  eligibleInvoices: Invoice[]
  employees: EmployeeOption[]
  invoiceSelectionLocked: boolean
  invoiceSelectionLoading: boolean
  saving: boolean
  onSelectInvoice: (invoiceId: number) => void
  onClose: () => void
  onSubmit: (input: CreateServiceOrderFromInvoiceInput) => void
}) {
  const [nextActionError, setNextActionError] = useState('')
  const form = useForm({
    defaultValues: {
      assignedToId: 0,
      dueDate: invoice.dueDate || '',
      description: '',
      nextAction: 'Confirm team and mobilisation',
    },
    onSubmit: ({ value }) => {
      const error = validateOrderCreation(value)
      setNextActionError(error)
      if (error) return
      onSubmit({
        invoiceId: invoice.id,
        assignedToId: value.assignedToId || null,
        dueDate: value.dueDate,
        description: value.description.trim(),
        nextAction: value.nextAction.trim(),
      })
    },
  })

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <form
        className="commercial-modal commercial-modal--xl"
        aria-label="Create Service Order"
        onMouseDown={(event) => event.stopPropagation()}
        onSubmit={(event) => {
          event.preventDefault()
          event.stopPropagation()
          void form.handleSubmit()
        }}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Create Service Order</h2>
            <p>Mobilise an eligible invoice into fulfillment</p>
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
            <h3>Commercial source</h3>
            <label className="commercial-field commercial-field--full">
              <span>Invoice *</span>
              <select
                value={invoice.id}
                disabled={invoiceSelectionLocked || invoiceSelectionLoading}
                onChange={(event) => onSelectInvoice(Number(event.target.value))}
              >
                {eligibleInvoices.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.invoiceNumber} — {item.serviceName} — {formatCurrency(item.totalAmount)}
                  </option>
                ))}
              </select>
              {invoiceSelectionLoading ? <small>Loading invoice…</small> : null}
            </label>

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
                <div className="commercial-kl">Order value</div>
                <b>{formatCurrency(invoice.totalAmount)}</b>
              </div>
              <div>
                <div className="commercial-kl">Paid</div>
                <b>{formatCurrency(invoice.amountPaid)}</b>
              </div>
              <div>
                <div className="commercial-kl">Payment status</div>
                <b>{invoice.status.replaceAll('_', ' ')}</b>
              </div>
              <div>
                <div className="commercial-kl">Threshold</div>
                <b>Met</b>
              </div>
            </div>
          </section>

          <section className="commercial-form-section">
            <h3>Mobilisation</h3>
            <div className="commercial-form-grid">
              <form.Field name="assignedToId">
                {(field) => (
                  <label className="commercial-field">
                    <span>Assigned employee</span>
                    <select
                      value={field.state.value}
                      onChange={(event) => field.handleChange(Number(event.target.value))}
                    >
                      <option value={0}>Unassigned</option>
                      {employees.map((employee) => (
                        <option key={employee.id} value={employee.id}>
                          {employee.name}
                          {employee.designation ? ` — ${employee.designation}` : ''}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </form.Field>

              <form.Field name="dueDate">
                {(field) => (
                  <label className="commercial-field">
                    <span>Due date</span>
                    <input
                      type="date"
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                    />
                  </label>
                )}
              </form.Field>

              <form.Field name="description">
                {(field) => (
                  <label className="commercial-field commercial-field--full">
                    <span>Fulfillment description</span>
                    <textarea
                      rows={4}
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                      placeholder="Operational context for the delivery team"
                    />
                  </label>
                )}
              </form.Field>

              <form.Field name="nextAction">
                {(field) => (
                  <label className="commercial-field commercial-field--full">
                    <span>Next action *</span>
                    <input
                      value={field.state.value}
                      onChange={(event) => {
                        if (nextActionError) setNextActionError('')
                        field.handleChange(event.target.value)
                      }}
                    />
                    {nextActionError ? (
                      <small className="commercial-field-error">{nextActionError}</small>
                    ) : null}
                  </label>
                )}
              </form.Field>
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
            disabled={saving || invoiceSelectionLoading}
          >
            {saving ? 'Creating…' : 'Create Service Order'}
          </button>
        </footer>
      </form>
    </div>
  )
}
