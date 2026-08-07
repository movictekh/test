import { IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'

import type { ServiceFeedback, UpdateFeedbackInput } from '../types/experience-intelligence.types'

export function FeedbackDetailWorkspace({
  feedback,
  saving,
  onClose,
  onSave,
}: {
  feedback: ServiceFeedback
  saving: boolean
  onClose: () => void
  onSave: (input: UpdateFeedbackInput) => void
}) {
  const form = useForm({
    defaultValues: {
      status: feedback.status,
      correctiveAction: feedback.correctiveAction,
      followUpAt: feedback.followUpAt ?? '',
    },
  })

  return (
    <div className="experience-modal-backdrop" onMouseDown={onClose}>
      <section
        className="experience-modal"
        role="dialog"
        aria-modal="true"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="experience-modal-header">
          <div>
            <h2>{feedback.id}</h2>
            <div className="experience-card-subtitle">
              {feedback.client} · {feedback.service}
            </div>
          </div>
          <button type="button" onClick={onClose} aria-label="Close">
            <IconX size={16} />
          </button>
        </header>

        <div className="experience-modal-body">
          <div className="experience-feedback-detail">
            <div>
              <span>Order</span>
              <b>{feedback.orderId}</b>
            </div>
            <div>
              <span>Rating</span>
              <b>{feedback.rating}/5</b>
            </div>
            <div>
              <span>Type</span>
              <b>{feedback.type}</b>
            </div>
            <div>
              <span>Date</span>
              <b>{feedback.date}</b>
            </div>
          </div>

          <div className="experience-notice">
            <b>Client comment</b>
            <p>{feedback.comment}</p>
          </div>

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

          <form.Field name="correctiveAction">
            {(field) => (
              <label className="experience-field">
                <span>Corrective action / internal note</span>
                <textarea
                  value={field.state.value}
                  onChange={(event) => field.handleChange(event.target.value)}
                />
              </label>
            )}
          </form.Field>

          <form.Field name="followUpAt">
            {(field) => (
              <label className="experience-field">
                <span>Follow-up date</span>
                <input
                  type="date"
                  value={field.state.value}
                  onChange={(event) => field.handleChange(event.target.value)}
                />
              </label>
            )}
          </form.Field>
        </div>

        <footer className="experience-modal-footer">
          <button type="button" className="experience-btn" onClick={onClose}>
            Close
          </button>
          <button
            type="button"
            className="experience-btn experience-btn-primary"
            disabled={saving}
            onClick={() =>
              onSave({
                status: form.state.values.status,
                correctiveAction: form.state.values.correctiveAction,
                ...(form.state.values.followUpAt
                  ? { followUpAt: form.state.values.followUpAt }
                  : {}),
              })
            }
          >
            Save Follow-up
          </button>
        </footer>
      </section>
    </div>
  )
}
