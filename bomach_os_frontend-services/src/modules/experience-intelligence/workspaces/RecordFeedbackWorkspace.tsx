import { IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useState } from 'react'

import type { ServiceOrder } from '@/modules/fulfillment/types/fulfillment.types'

import type { CreateFeedbackInput } from '../types/experience-intelligence.types'

export function RecordFeedbackWorkspace({
  orders,
  initialOrderId = '',
  saving,
  onClose,
  onSubmit,
}: {
  orders: ServiceOrder[]
  initialOrderId?: string
  saving: boolean
  onClose: () => void
  onSubmit: (input: CreateFeedbackInput) => void
}) {
  const [error, setError] = useState('')
  const form = useForm({
    defaultValues: {
      orderId: initialOrderId || orders[0]?.id || '',
      type: 'Completion' as const,
      rating: 5 as const,
      status: 'Closed' as const,
      comment: '',
      correctiveAction: '',
    },
  })

  return (
    <div className="experience-modal-backdrop" onMouseDown={onClose}>
      <form
        className="experience-modal"
        onMouseDown={(event) => event.stopPropagation()}
        onSubmit={(event) => {
          event.preventDefault()
          const value = form.state.values

          if (!value.orderId || !value.comment.trim()) {
            setError('Select an order and enter the client comment.')
            return
          }

          setError('')
          onSubmit(value)
        }}
      >
        <header className="experience-modal-header">
          <h2>Record Client Feedback</h2>
          <button type="button" onClick={onClose} aria-label="Close">
            <IconX size={16} />
          </button>
        </header>

        <div className="experience-modal-body">
          {error ? <div className="experience-notice experience-notice-red">{error}</div> : null}

          <div className="experience-form-grid">
            <form.Field name="orderId">
              {(field) => (
                <label className="experience-field">
                  <span>Order</span>
                  <select
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                  >
                    {orders.map((order) => (
                      <option key={order.id} value={order.id}>
                        {order.id} — {order.client}
                      </option>
                    ))}
                  </select>
                </label>
              )}
            </form.Field>

            <form.Field name="type">
              {(field) => (
                <label className="experience-field">
                  <span>Type</span>
                  <select
                    value={field.state.value}
                    onChange={(event) =>
                      field.handleChange(event.target.value as typeof field.state.value)
                    }
                  >
                    <option>Completion</option>
                    <option>Milestone</option>
                    <option>Complaint</option>
                    <option>Defect / Rework</option>
                    <option>Testimonial</option>
                    <option>Referral</option>
                  </select>
                </label>
              )}
            </form.Field>

            <form.Field name="rating">
              {(field) => (
                <label className="experience-field">
                  <span>Rating</span>
                  <select
                    value={field.state.value}
                    onChange={(event) =>
                      field.handleChange(Number(event.target.value) as typeof field.state.value)
                    }
                  >
                    <option value={5}>5 — Excellent</option>
                    <option value={4}>4 — Good</option>
                    <option value={3}>3 — Satisfactory</option>
                    <option value={2}>2 — Poor</option>
                    <option value={1}>1 — Very poor</option>
                  </select>
                </label>
              )}
            </form.Field>

            <form.Field name="status">
              {(field) => (
                <label className="experience-field">
                  <span>Status</span>
                  <select
                    value={field.state.value}
                    onChange={(event) =>
                      field.handleChange(event.target.value as typeof field.state.value)
                    }
                  >
                    <option>Closed</option>
                    <option>Open</option>
                    <option>Action Required</option>
                  </select>
                </label>
              )}
            </form.Field>

            <form.Field name="comment">
              {(field) => (
                <label className="experience-field experience-field-full">
                  <span>Client comment</span>
                  <textarea
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                  />
                </label>
              )}
            </form.Field>

            <form.Field name="correctiveAction">
              {(field) => (
                <label className="experience-field experience-field-full">
                  <span>Corrective action / internal note</span>
                  <textarea
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                  />
                </label>
              )}
            </form.Field>
          </div>
        </div>

        <footer className="experience-modal-footer">
          <button type="button" className="experience-btn" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="experience-btn experience-btn-primary" disabled={saving}>
            {saving ? 'Saving...' : 'Save Feedback'}
          </button>
        </footer>
      </form>
    </div>
  )
}
