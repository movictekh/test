import { IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useState } from 'react'

import type { CreateExecutionTaskInput } from '../types/fulfillment.types'

export function CreateTaskWorkspace({
  initialOrderId = '',
  saving,
  onClose,
  onSubmit,
}: {
  initialOrderId?: string
  saving: boolean
  onClose: () => void
  onSubmit: (input: CreateExecutionTaskInput) => void
}) {
  const [error, setError] = useState('')
  const defaultValues: CreateExecutionTaskInput = {
    title: '',
    orderId: initialOrderId,
    owner: '',
    dueAt: '2026-07-16',
    priority: 'Normal',
    evidenceRequired: true,
    instructions: '',
  }

  const form = useForm({ defaultValues })

  const submit = () => {
    const value = form.state.values
    if (!value.title.trim() || !value.orderId.trim() || !value.owner.trim() || !value.dueAt) {
      setError('Complete the task title, order, owner and due date.')
      return
    }
    setError('')
    onSubmit(value)
  }

  return (
    <div className="fulfillment-modal-backdrop" onMouseDown={onClose}>
      <form
        className="fulfillment-modal"
        aria-label="Create Execution Task"
        onMouseDown={(event) => event.stopPropagation()}
        onSubmit={(event) => {
          event.preventDefault()
          submit()
        }}
      >
        <header className="fulfillment-modal-header">
          <h2>Create Execution Task</h2>
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
            <form.Field name="title">
              {(field) => (
                <label className="fulfillment-field">
                  <span>Task title</span>
                  <input
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                  />
                </label>
              )}
            </form.Field>

            <form.Field name="orderId">
              {(field) => (
                <label className="fulfillment-field">
                  <span>Order / request</span>
                  <input
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                  />
                </label>
              )}
            </form.Field>

            <form.Field name="owner">
              {(field) => (
                <label className="fulfillment-field">
                  <span>Owner</span>
                  <input
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                  />
                </label>
              )}
            </form.Field>

            <form.Field name="dueAt">
              {(field) => (
                <label className="fulfillment-field">
                  <span>Due date</span>
                  <input
                    type="date"
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                  />
                </label>
              )}
            </form.Field>

            <form.Field name="priority">
              {(field) => (
                <label className="fulfillment-field">
                  <span>Priority</span>
                  <select
                    value={field.state.value}
                    onChange={(event) =>
                      field.handleChange(event.target.value as typeof field.state.value)
                    }
                  >
                    <option>Normal</option>
                    <option>High</option>
                    <option>Critical</option>
                  </select>
                </label>
              )}
            </form.Field>

            <form.Field name="evidenceRequired">
              {(field) => (
                <label className="fulfillment-field">
                  <span>Evidence required</span>
                  <select
                    value={field.state.value ? 'Yes' : 'No'}
                    onChange={(event) => field.handleChange(event.target.value === 'Yes')}
                  >
                    <option>Yes</option>
                    <option>No</option>
                  </select>
                </label>
              )}
            </form.Field>

            <form.Field name="instructions">
              {(field) => (
                <label className="fulfillment-field fulfillment-field-full">
                  <span>Instructions / acceptance criteria</span>
                  <textarea
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
            {saving ? 'Creating...' : 'Create Task'}
          </button>
        </footer>
      </form>
    </div>
  )
}
