import { IconX } from '@tabler/icons-react'
import { useState } from 'react'

import { formatCurrency } from '@/shared/lib/formatters'

import type { ApprovalQueueItem } from '../approval-queue/approval-queue.types'

function statusClass(status: ApprovalQueueItem['status']) {
  if (status === 'approved') return 'commercial-pill-green'
  if (status === 'rejected') return 'commercial-pill-gray'
  return 'commercial-pill-yellow'
}

export function ApprovalQueueDetailLiveWorkspace({
  item,
  canApprove,
  canReject,
  saving,
  onClose,
  onApprove,
  onReject,
}: {
  item: ApprovalQueueItem
  canApprove: boolean
  canReject: boolean
  saving: boolean
  onClose: () => void
  onApprove: () => void
  onReject: (reason: string) => void
}) {
  const [rejecting, setRejecting] = useState(false)
  const [reason, setReason] = useState('')
  const [reasonError, setReasonError] = useState('')

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="commercial-modal commercial-modal--xl"
        role="dialog"
        aria-modal="true"
        aria-label={`Approval ${item.refNumber}`}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>{item.refNumber}</h2>
            <p>
              {item.sourceDisplay} · {item.subject}
            </p>
          </div>
          <div className="commercial-modal-header-meta">
            <span className={`commercial-pill ${statusClass(item.status)}`}>
              {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
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
            <div className="commercial-approval-summary">
              <div className="commercial-approval-amount-card">
                <span className="commercial-approval-amount-label">Approval amount</span>
                <strong>{item.amount == null ? '—' : formatCurrency(item.amount)}</strong>
                <small>
                  {item.sourceDisplay} · {item.refNumber}
                </small>
              </div>
            </div>

            <h3>Approval details</h3>
            <div className="commercial-info-grid">
              <div>
                <div className="commercial-kl">Type</div>
                <b>{item.sourceDisplay}</b>
              </div>
              <div>
                <div className="commercial-kl">Reference</div>
                <b>{item.refNumber}</b>
              </div>
              <div>
                <div className="commercial-kl">Requester</div>
                <b>{item.requesterName || '—'}</b>
              </div>
              <div>
                <div className="commercial-kl">Approver</div>
                <b>{item.approverName || '—'}</b>
              </div>
              <div>
                <div className="commercial-kl">Created</div>
                <b>{new Date(item.createdAt).toLocaleString('en-GB')}</b>
              </div>
              <div className="commercial-info-full">
                <div className="commercial-kl">Subject</div>
                <p>{item.subject}</p>
              </div>
            </div>
          </section>

          {rejecting ? (
            <section className="commercial-form-section">
              <h3>Reject approval</h3>
              <label className="commercial-field commercial-field--full">
                <span>{item.source === 'deliverable' ? 'Reason *' : 'Reason'}</span>
                <textarea
                  rows={4}
                  value={reason}
                  onChange={(event) => {
                    if (reasonError) setReasonError('')
                    setReason(event.target.value)
                  }}
                  placeholder="Add a reason for this decision"
                />
                {reasonError ? (
                  <small className="commercial-field-error">{reasonError}</small>
                ) : null}
              </label>
            </section>
          ) : null}
        </div>

        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" disabled={saving} onClick={onClose}>
            Close
          </button>

          <div className="commercial-modal-footer-actions">
            {rejecting ? (
              <>
                <button
                  type="button"
                  className="commercial-btn"
                  disabled={saving}
                  onClick={() => {
                    setRejecting(false)
                    setReason('')
                    setReasonError('')
                  }}
                >
                  Back
                </button>
                <button
                  type="button"
                  className="commercial-btn"
                  disabled={saving}
                  onClick={() => {
                    if (item.source === 'deliverable' && !reason.trim()) {
                      setReasonError('Add a reason before rejecting this deliverable.')
                      return
                    }
                    onReject(reason.trim())
                  }}
                >
                  {saving ? 'Saving...' : 'Confirm Rejection'}
                </button>
              </>
            ) : (
              <>
                {canReject ? (
                  <button
                    type="button"
                    className="commercial-btn"
                    disabled={saving}
                    onClick={() => setRejecting(true)}
                  >
                    Reject
                  </button>
                ) : null}

                {canApprove ? (
                  <button
                    type="button"
                    className="commercial-btn commercial-btn-green"
                    disabled={saving}
                    onClick={onApprove}
                  >
                    {saving ? 'Saving...' : item.actionLabel || 'Approve'}
                  </button>
                ) : null}
              </>
            )}
          </div>
        </footer>
      </section>
    </div>
  )
}
