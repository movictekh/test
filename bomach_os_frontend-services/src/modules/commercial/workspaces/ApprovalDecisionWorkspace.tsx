import { IconX } from '@tabler/icons-react'
import { useState } from 'react'

import { approvalStatusClass, commercialMoney } from '../commercial.ui'
import type { CommercialApproval, DecideApprovalInput } from '../types/commercial.types'
import { validateApprovalDecision } from './approval-workflow.rules'

export function ApprovalDecisionWorkspace({
  approval,
  saving,
  onClose,
  canApprove,
  canReject,
  onDecide,
}: {
  approval: CommercialApproval
  saving: boolean
  onClose: () => void
  canApprove: boolean
  canReject: boolean
  onDecide: (input: DecideApprovalInput) => void
}) {
  const [note, setNote] = useState('')
  const [errors, setErrors] = useState<Partial<Record<keyof DecideApprovalInput, string>>>({})

  const submit = (decision: DecideApprovalInput['decision']) => {
    const input: DecideApprovalInput = {
      approvalId: approval.id,
      decision,
      note: note.trim(),
    }
    const nextErrors = validateApprovalDecision(input)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length === 0) {
      onDecide(input)
    }
  }

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="commercial-modal commercial-modal--xl"
        role="dialog"
        aria-modal="true"
        aria-label={`Approval ${approval.id}`}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Approval {approval.id}</h2>
            <p>
              {approval.entityType} · {approval.entityId}
            </p>
          </div>
          <div className="commercial-modal-header-meta">
            <span className={`commercial-pill ${approvalStatusClass(approval.status)}`}>
              {approval.status}
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
            <h3>Approval request</h3>
            <p className="commercial-form-note">
              Requested {approval.requestedAt} · Due {approval.dueAt}
            </p>
            <div className="commercial-quote-pricing-layout">
              <div className="commercial-info-grid">
                <div>
                  <div className="commercial-kl">Subject</div>
                  <b>{approval.subject}</b>
                </div>
                <div>
                  <div className="commercial-kl">Client</div>
                  <b>{approval.client}</b>
                </div>
                <div>
                  <div className="commercial-kl">Requester</div>
                  <b>{approval.requestedBy}</b>
                </div>
                <div>
                  <div className="commercial-kl">Approver</div>
                  <b>{approval.assignedTo}</b>
                </div>
                <div>
                  <div className="commercial-kl">Reference</div>
                  <b>{approval.entityId}</b>
                </div>
                <div>
                  <div className="commercial-kl">Type</div>
                  <b>{approval.entityType}</b>
                </div>
              </div>
              <article className="commercial-quote-value-card">
                <div className="commercial-kpi-label">
                  {approval.amount > 0 ? 'Value at stake' : 'Operational checkpoint'}
                </div>
                <div className="commercial-kpi-value">
                  {approval.amount > 0 ? commercialMoney.format(approval.amount) : 'No cash value'}
                </div>
                <div className="commercial-kpi-note">
                  {approval.entityType} approval routed to {approval.assignedTo}
                </div>
              </article>
            </div>
          </section>

          {approval.status === 'Pending' && (canApprove || canReject) ? (
            <section className="commercial-form-section">
              <h3>Decision note</h3>
              <p className="commercial-form-note">
                Record the accountable reason before approving or rejecting
              </p>
              <label className="commercial-field commercial-field--full">
                <span>Decision note *</span>
                <textarea rows={4} value={note} onChange={(event) => setNote(event.target.value)} />
                {errors.note ? <em>{errors.note}</em> : null}
              </label>
            </section>
          ) : null}

          {approval.decisionNote ? (
            <section className="commercial-form-section">
              <h3>Recorded decision</h3>
              <div className="commercial-timeline-list">
                <article className="commercial-tl">
                  <b>{approval.status}</b>
                  <p>{approval.decisionNote}</p>
                  {approval.decidedAt ? <time>{approval.decidedAt.slice(0, 10)}</time> : null}
                </article>
              </div>
            </section>
          ) : null}
        </div>

        <footer className="commercial-modal-footer">
          <div className="commercial-modal-footer-start">
            <button type="button" className="commercial-btn" onClick={onClose} disabled={saving}>
              Close
            </button>
          </div>
          <div className="commercial-modal-footer-actions">
            {approval.status === 'Pending' && (canApprove || canReject) ? (
              <>
                {canReject ? (
                  <button
                    type="button"
                    className="commercial-btn"
                    disabled={saving}
                    onClick={() => submit('reject')}
                  >
                    {saving ? 'Saving...' : 'Reject'}
                  </button>
                ) : null}
                {canApprove ? (
                  <button
                    type="button"
                    className="commercial-btn commercial-btn-green"
                    disabled={saving}
                    onClick={() => submit('approve')}
                  >
                    {saving ? 'Saving...' : 'Approve'}
                  </button>
                ) : null}
              </>
            ) : null}
          </div>
        </footer>
      </section>
    </div>
  )
}
