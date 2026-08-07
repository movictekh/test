import { IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useState } from 'react'

import { formatNumberFieldValue, parseNumberFieldValue } from '@/shared/lib/number-input'

import type { AddOrderUpdateInput, ServiceOrder } from '../types/fulfillment.types'

export function OrderUpdateWorkspace({
  order,
  saving,
  onClose,
  onSubmit,
}: {
  order: ServiceOrder
  saving: boolean
  onClose: () => void
  onSubmit: (input: AddOrderUpdateInput) => void
}) {
  const [error, setError] = useState('')
  const form = useForm({
    defaultValues: {
      orderId: order.id,
      type: 'Progress update',
      visibility: 'Internal and client' as const,
      note: '',
      progress: order.progress,
      nextAction: '',
    } satisfies AddOrderUpdateInput,
  })

  const submit = () => {
    const value = form.state.values
    if (!value.note.trim()) {
      setError('Add the progress update before saving.')
      return
    }
    setError('')
    onSubmit(value)
  }

  return (
    <div className="fulfillment-modal-backdrop fulfillment-modal-layer-2">
      <form
        className="fulfillment-modal"
        onSubmit={(event) => {
          event.preventDefault()
          submit()
        }}
      >
        <header className="fulfillment-modal-header">
          <h2>Add Order Progress Update</h2>
          <button
            type="button"
            className="fulfillment-modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            <IconX size={16} />
          </button>
        </header>

        <div className="fulfillment-modal-body">
          {error ? <div className="fulfillment-notice fulfillment-notice-red">{error}</div> : null}
          <div className="fulfillment-form-grid">
            <form.Field name="type">
              {(field) => (
                <label className="fulfillment-field">
                  <span>Update type</span>
                  <select
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                  >
                    <option>Progress update</option>
                    <option>Site report</option>
                    <option>Client communication</option>
                    <option>Delay / blocker</option>
                    <option>Inspection</option>
                    <option>Material update</option>
                    <option>Decision</option>
                  </select>
                </label>
              )}
            </form.Field>

            <form.Field name="visibility">
              {(field) => (
                <label className="fulfillment-field">
                  <span>Visibility</span>
                  <select
                    value={field.state.value}
                    onChange={(event) =>
                      field.handleChange(event.target.value as typeof field.state.value)
                    }
                  >
                    <option>Internal and client</option>
                    <option>Internal only</option>
                    <option>Management only</option>
                  </select>
                </label>
              )}
            </form.Field>

            <form.Field name="note">
              {(field) => (
                <label className="fulfillment-field fulfillment-field-full">
                  <span>Detailed update</span>
                  <textarea
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                  />
                </label>
              )}
            </form.Field>

            <form.Field name="progress">
              {(field) => (
                <label className="fulfillment-field">
                  <span>Progress (%)</span>
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

            <form.Field name="nextAction">
              {(field) => (
                <label className="fulfillment-field">
                  <span>Next action</span>
                  <input
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                  />
                </label>
              )}
            </form.Field>
          </div>
        </div>

        <footer className="fulfillment-modal-footer">
          <button type="button" className="fulfillment-btn" onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className="fulfillment-btn fulfillment-btn-primary"
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Update'}
          </button>
        </footer>
      </form>
    </div>
  )
}
