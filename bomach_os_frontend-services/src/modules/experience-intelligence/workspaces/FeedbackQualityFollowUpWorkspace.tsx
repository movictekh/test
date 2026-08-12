import { IconExternalLink, IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useNavigate } from '@tanstack/react-router'
import type {
  ClientFeedback,
  FeedbackStatus,
  UpdateQualityFollowUpInput,
} from '../feedback/feedback.types'
import { feedbackStatusOptions } from '../feedback/feedback.types'
const dt = (v: string) => {
  if (!v) return '—'
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? v : d.toLocaleString()
}
export function FeedbackQualityFollowUpWorkspace({
  feedback,
  canUpdate,
  saving,
  onClose,
  onSave,
}: {
  feedback: ClientFeedback
  canUpdate: boolean
  saving: boolean
  onClose: () => void
  onSave: (i: UpdateQualityFollowUpInput) => void
}) {
  const navigate = useNavigate()
  const form = useForm({
    defaultValues: { status: feedback.status, internalNote: feedback.internalNote },
  })
  return (
    <div className="experience-modal-backdrop" onMouseDown={onClose}>
      <section
        className="experience-modal"
        role="dialog"
        aria-modal="true"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <header className="experience-modal-header">
          <div>
            <h2>Feedback #{feedback.id}</h2>
            <div className="experience-card-subtitle">
              {feedback.clientName} · {feedback.serviceName}
            </div>
          </div>
          <button type="button" onClick={onClose}>
            <IconX size={16} />
          </button>
        </header>
        <div className="experience-modal-body">
          <div className="experience-feedback-detail">
            <div>
              <span>Order</span>
              <b>{feedback.orderNumber || `#${feedback.orderId}`}</b>
            </div>
            <div>
              <span>Rating</span>
              <b>{feedback.rating}/5</b>
            </div>
            <div>
              <span>Type</span>
              <b>{feedback.feedbackTypeDisplay}</b>
            </div>
            <div>
              <span>Submitted</span>
              <b>{dt(feedback.createdAt)}</b>
            </div>
          </div>
          <div className="experience-notice">
            <b>Client feedback</b>
            <p>{feedback.comment || 'No client comment recorded.'}</p>
          </div>
          <div className="experience-quality-origin">
            <div>
              <span>Client</span>
              <b>{feedback.clientName}</b>
            </div>
            <div>
              <span>Service</span>
              <b>{feedback.serviceName}</b>
            </div>
            <div>
              <span>Recorded by</span>
              <b>{feedback.recordedBy.displayName}</b>
              <small>{feedback.recordedBy.email}</small>
            </div>
            <div>
              <span>Updated</span>
              <b>{dt(feedback.updatedAt)}</b>
            </div>
          </div>
          <div className="experience-quality-separator">
            <b>Quality Follow-up</b>
            <span>
              Client rating, feedback type and comment are read-only in this internal application.
            </span>
          </div>
          <form.Field name="status">
            {(field) => (
              <label className="experience-field">
                <span>Status</span>
                <select
                  value={field.state.value}
                  disabled={!canUpdate}
                  onChange={(e) => field.handleChange(e.target.value as FeedbackStatus)}
                >
                  {feedbackStatusOptions.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </form.Field>
          <form.Field name="internalNote">
            {(field) => (
              <label className="experience-field">
                <span>Corrective action / internal note</span>
                <textarea
                  value={field.state.value}
                  disabled={!canUpdate}
                  onChange={(e) => field.handleChange(e.target.value)}
                  placeholder="Record the internal response, corrective action or resolution."
                />
              </label>
            )}
          </form.Field>
        </div>
        <footer className="experience-modal-footer experience-modal-footer--split">
          <button
            className="experience-btn"
            type="button"
            onClick={() =>
              void navigate({
                to: '/app/$section',
                params: { section: 'service-orders' },
                search: { order: String(feedback.orderId) },
              })
            }
          >
            <IconExternalLink size={13} />
            Open Service Order
          </button>
          <div>
            <button className="experience-btn" type="button" onClick={onClose}>
              Close
            </button>
            {canUpdate ? (
              <button
                className="experience-btn experience-btn-primary"
                type="button"
                disabled={saving}
                onClick={() =>
                  onSave({
                    status: form.state.values.status,
                    internalNote: form.state.values.internalNote.trim(),
                  })
                }
              >
                {saving ? 'Saving...' : 'Save Quality Follow-up'}
              </button>
            ) : null}
          </div>
        </footer>
      </section>
    </div>
  )
}
