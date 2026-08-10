import { IconX } from '@tabler/icons-react'
import { useState } from 'react'

import { getApprovalCapabilities } from '../approvals/approval-capabilities'
import type { ApprovalFlow, ApprovalRequest } from '../approvals/approval.types'
import { validateApprovalDecision } from '../approvals/approval.validation'

function statusClass(status: ApprovalRequest['status']) {
  if (status === 'approved') return 'commercial-pill-green'
  if (status === 'rejected' || status === 'cancelled') {
    return 'commercial-pill-gray'
  }
  return 'commercial-pill-yellow'
}

function metadataEntries(metadata: Record<string, unknown>) {
  return Object.entries(metadata).filter(([, value]) =>
    ['string', 'number', 'boolean'].includes(typeof value),
  )
}

export function ApprovalDetailLiveWorkspace({
  request,
  flow,
  currentUserId,
  canApprove,
  canReject,
  canCancel,
  saving,
  onClose,
  onApprove,
  onReject,
  onCancel,
}: {
  request: ApprovalRequest
  flow: ApprovalFlow | null
  currentUserId: number | null
  canApprove: boolean
  canReject: boolean
  canCancel: boolean
  saving: boolean
  onClose: () => void
  onApprove: (comment: string) => void
  onReject: (comment: string) => void
  onCancel: () => void
}) {
  const [comment, setComment] = useState('')
  const [decisionError, setDecisionError] = useState('')
  const capabilities = getApprovalCapabilities(request, currentUserId)
  const metadata = metadataEntries(request.metadata)

  const submit = (decision: 'approve' | 'reject') => {
    const error = validateApprovalDecision(decision, comment)
    setDecisionError(error)
    if (error) return
    if (decision === 'approve') onApprove(comment.trim())
    else onReject(comment.trim())
  }

  const flowSteps =
    flow?.steps ??
    Array.from({ length: request.totalSteps }, (_, index) => ({
      id: index + 1,
      stepOrder: index + 1,
      stepName:
        index + 1 === request.currentStep
          ? request.pendingStepName || `Step ${index + 1}`
          : request.decisions.find((d) => d.stepOrder === index + 1)?.stepName ||
            `Step ${index + 1}`,
      requiredLevel: '',
      requiredLevelDisplay:
        index + 1 === request.currentStep ? request.pendingStepRequiredLevelDisplay : '',
    }))

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="commercial-modal commercial-modal--xl"
        role="dialog"
        aria-modal="true"
        aria-label={`Approval ${request.approvalRequestId}`}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>{request.approvalRequestId}</h2>
            <p>
              {request.actionTypeDisplay} · {request.flowName}
            </p>
          </div>
          <div className="commercial-modal-header-meta">
            <span className={`commercial-pill ${statusClass(request.status)}`}>
              {request.statusDisplay}
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
            <h3>Request details</h3>
            <div className="commercial-info-grid">
              <div className="commercial-info-full">
                <div className="commercial-kl">Title</div>
                <b>{request.title}</b>
              </div>
              <div>
                <div className="commercial-kl">Requested by</div>
                <b>{request.createdByName || '—'}</b>
              </div>
              <div>
                <div className="commercial-kl">Created</div>
                <b>{new Date(request.createdAt).toLocaleString('en-GB')}</b>
              </div>
              <div>
                <div className="commercial-kl">Flow</div>
                <b>{request.flowName}</b>
              </div>
              <div>
                <div className="commercial-kl">Type</div>
                <b>{request.actionTypeDisplay}</b>
              </div>
              <div className="commercial-info-full">
                <div className="commercial-kl">Description</div>
                <p>{request.description}</p>
              </div>
            </div>
          </section>

          <section className="commercial-form-section">
            <div className="commercial-form-section-heading">
              <div>
                <h3>Approval progress</h3>
                <p>
                  Step {Math.min(request.currentStep, request.totalSteps)} of {request.totalSteps}
                </p>
              </div>
              {request.status === 'pending' ? (
                <div className="commercial-quote-total-chip">
                  <span>Current step</span>
                  <b>{request.pendingStepName || `Step ${request.currentStep}`}</b>
                </div>
              ) : null}
            </div>

            {request.status === 'pending' ? (
              <div className="commercial-info-grid">
                <div>
                  <div className="commercial-kl">Required level</div>
                  <b>{request.pendingStepRequiredLevelDisplay || '—'}</b>
                </div>
                <div>
                  <div className="commercial-kl">Completed decisions</div>
                  <b>{request.decisions.length}</b>
                </div>
              </div>
            ) : null}

            <div className="commercial-timeline-list">
              {flowSteps.map((step) => {
                const decision = request.decisions.find((item) => item.stepOrder === step.stepOrder)
                const current =
                  request.status === 'pending' && step.stepOrder === request.currentStep

                return (
                  <article key={step.id} className="commercial-tl">
                    <b>
                      Step {step.stepOrder} — {step.stepName}
                    </b>
                    {decision ? (
                      <>
                        <p>
                          {decision.decisionDisplay}
                          {decision.approverName ? ` by ${decision.approverName}` : ''}
                        </p>
                        {decision.comment ? <p>{decision.comment}</p> : null}
                        <time>{new Date(decision.createdAt).toLocaleString('en-GB')}</time>
                      </>
                    ) : current ? (
                      <p>Awaiting {step.requiredLevelDisplay || 'approval'}</p>
                    ) : (
                      <p>Pending</p>
                    )}
                  </article>
                )
              })}
            </div>
          </section>

          {metadata.length > 0 ? (
            <section className="commercial-form-section">
              <h3>Additional context</h3>
              <div className="commercial-info-grid">
                {metadata.map(([key, value]) => (
                  <div key={key}>
                    <div className="commercial-kl">{key.replaceAll('_', ' ')}</div>
                    <b>{String(value)}</b>
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          {capabilities.decide && (canApprove || canReject) ? (
            <section className="commercial-form-section">
              <h3>Decision</h3>
              <label className="commercial-field commercial-field--full">
                <span>Comment</span>
                <textarea
                  rows={4}
                  value={comment}
                  onChange={(event) => {
                    if (decisionError) setDecisionError('')
                    setComment(event.target.value)
                  }}
                  placeholder="Add context for this decision"
                />
                {decisionError ? (
                  <small className="commercial-field-error">{decisionError}</small>
                ) : null}
              </label>
            </section>
          ) : null}
        </div>

        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" onClick={onClose} disabled={saving}>
            Close
          </button>

          <div className="commercial-modal-footer-actions">
            {capabilities.cancel && canCancel ? (
              <button type="button" className="commercial-btn" disabled={saving} onClick={onCancel}>
                Cancel Request
              </button>
            ) : null}

            {capabilities.decide && canReject ? (
              <button
                type="button"
                className="commercial-btn"
                disabled={saving}
                onClick={() => submit('reject')}
              >
                {saving ? 'Saving...' : 'Reject'}
              </button>
            ) : null}

            {capabilities.decide && canApprove ? (
              <button
                type="button"
                className="commercial-btn commercial-btn-green"
                disabled={saving}
                onClick={() => submit('approve')}
              >
                {saving ? 'Saving...' : 'Approve'}
              </button>
            ) : null}
          </div>
        </footer>
      </section>
    </div>
  )
}
