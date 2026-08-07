import { IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useMemo, useState } from 'react'

import type {
  CommercialInvoice,
  CommercialQuotation,
  CreateInvoiceInput,
} from '../types/commercial.types'
import { getInvoiceEligibleQuotations, validateInvoiceInput } from './commercial-finance.rules'

function defaultDueDate() {
  const date = new Date()
  date.setDate(date.getDate() + 14)
  return date.toISOString().slice(0, 10)
}

export function InvoiceBuilderWorkspace({
  quotations,
  invoices,
  initialQuotationId,
  saving,
  onClose,
  onSubmit,
}: {
  quotations: CommercialQuotation[]
  invoices: CommercialInvoice[]
  initialQuotationId?: string
  saving: boolean
  onClose: () => void
  onSubmit: (input: CreateInvoiceInput) => void
}) {
  const eligible = useMemo(
    () => getInvoiceEligibleQuotations(quotations, invoices),
    [invoices, quotations],
  )
  const initial = eligible.find((quotation) => quotation.id === initialQuotationId) ?? eligible[0]
  const [errors, setErrors] = useState<Partial<Record<keyof CreateInvoiceInput, string>>>({})

  const defaultValues: CreateInvoiceInput = {
    quotationId: initial?.id ?? '',
    dueAt: defaultDueDate(),
    issueNow: true,
  }

  const form = useForm({
    defaultValues,
  })

  const submit = () => {
    const value = form.state.values
    const nextErrors = validateInvoiceInput(value)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length === 0) onSubmit(value)
  }

  return (
    <div className="commercial-modal-backdrop" onMouseDown={onClose}>
      <form
        className="commercial-modal"
        onSubmit={(event) => {
          event.preventDefault()
          submit()
        }}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Create Invoice</h2>
            <p>Generate billing from an accepted quotation</p>
          </div>
          <button type="button" className="commercial-modal-close" onClick={onClose}>
            <IconX size={16} />
          </button>
        </header>

        <div className="commercial-modal-body">
          {eligible.length === 0 ? (
            <div className="commercial-empty">No accepted, uninvoiced quotation is available.</div>
          ) : (
            <div className="commercial-form-grid">
              <form.Field name="quotationId">
                {(field) => (
                  <label className="commercial-field commercial-field--full">
                    <span>Accepted quotation *</span>
                    <select
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                    >
                      {eligible.map((quotation) => (
                        <option key={quotation.id} value={quotation.id}>
                          {quotation.id} — {quotation.client} — {quotation.service}
                        </option>
                      ))}
                    </select>
                    {errors.quotationId ? <em>{errors.quotationId}</em> : null}
                  </label>
                )}
              </form.Field>

              <form.Field name="dueAt">
                {(field) => (
                  <label className="commercial-field">
                    <span>Due date *</span>
                    <input
                      type="date"
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                    />
                    {errors.dueAt ? <em>{errors.dueAt}</em> : null}
                  </label>
                )}
              </form.Field>

              <form.Field name="issueNow">
                {(field) => (
                  <label className="commercial-check">
                    <input
                      type="checkbox"
                      checked={field.state.value}
                      onChange={(event) => field.handleChange(event.target.checked)}
                    />
                    Issue invoice immediately
                  </label>
                )}
              </form.Field>
            </div>
          )}
        </div>

        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className="commercial-btn commercial-btn-primary"
            disabled={saving || eligible.length === 0}
          >
            {saving ? 'Creating...' : 'Create Invoice'}
          </button>
        </footer>
      </form>
    </div>
  )
}
