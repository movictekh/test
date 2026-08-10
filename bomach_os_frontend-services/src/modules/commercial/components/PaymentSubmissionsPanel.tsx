import { useState } from 'react'

import { formatCurrency } from '@/shared/lib/formatters'
import { EmptyState } from '@/shared/ui/empty-state'

import {
  paymentMethodOptions,
  type PaymentSubmission,
  type PaymentSubmissionStatus,
  type ReviewPaymentSubmissionInput,
} from '../billing/billing.types'

function paymentMethodLabel(value: string) {
  return paymentMethodOptions.find((item) => item.value === value)?.label ?? value
}

export function PaymentSubmissionsPanel({
  submissions,
  status,
  loading,
  error,
  onRetry,
  saving,
  canReview,
  onStatusChange,
  onReview,
}: {
  submissions: PaymentSubmission[]
  status: PaymentSubmissionStatus | ''
  loading: boolean
  error: string
  onRetry: () => void
  saving: boolean
  canReview: boolean
  onStatusChange: (status: PaymentSubmissionStatus | '') => void
  onReview: (submission: PaymentSubmission, input: ReviewPaymentSubmissionInput) => void
}) {
  const [rejectingId, setRejectingId] = useState<number | null>(null)
  const [reason, setReason] = useState('')

  if (loading) {
    return <div className="commercial-empty">Loading payment submissions...</div>
  }

  if (error) {
    return (
      <div className="commercial-empty">
        <p>{error}</p>
        <button type="button" className="commercial-btn commercial-btn-small" onClick={onRetry}>
          Retry
        </button>
      </div>
    )
  }

  return (
    <>
      <div className="commercial-filters">
        <select
          value={status}
          onChange={(event) => onStatusChange(event.target.value as PaymentSubmissionStatus | '')}
        >
          <option value="">All submission states</option>
          <option value="pending">Pending Review</option>
          <option value="confirmed">Confirmed</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>

      {submissions.length === 0 ? (
        <EmptyState
          title={
            status
              ? 'No payment submissions match the current filter'
              : 'No payment submissions yet'
          }
          description={
            status
              ? 'Try changing or clearing the submission status filter to review other payment updates.'
              : 'Client payment confirmations and proof of payment will appear here once they start coming in.'
          }
        />
      ) : (
        <div className="commercial-table-wrap">
          <table className="commercial-table">
            <thead>
              <tr>
                <th>Submission</th>
                <th>Invoice</th>
                <th>Amount</th>
                <th>Method</th>
                <th>Payment date</th>
                <th>Status</th>
                <th>Proof</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {submissions.map((submission) => (
                <tr key={submission.id}>
                  <td>
                    <b>{submission.reference}</b>
                    <small>{new Date(submission.createdAt).toLocaleDateString('en-GB')}</small>
                  </td>
                  <td>{submission.invoiceNumber}</td>
                  <td>{formatCurrency(submission.amount)}</td>
                  <td>{paymentMethodLabel(submission.paymentMethod)}</td>
                  <td>{submission.paymentDate}</td>
                  <td>
                    <span className="commercial-pill commercial-pill-blue">
                      {submission.statusDisplay}
                    </span>
                  </td>
                  <td>
                    {submission.proofOfPayment ? (
                      <a href={submission.proofOfPayment} target="_blank" rel="noreferrer">
                        Open proof
                      </a>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td>
                    {submission.status === 'pending' && canReview ? (
                      <div className="commercial-modal-footer-actions">
                        <button
                          type="button"
                          className="commercial-btn commercial-btn-small"
                          disabled={saving}
                          onClick={() => {
                            setRejectingId(submission.id)
                            setReason('')
                          }}
                        >
                          Reject
                        </button>
                        <button
                          type="button"
                          className="commercial-btn commercial-btn-small commercial-btn-green"
                          disabled={saving}
                          onClick={() => onReview(submission, { status: 'confirmed' })}
                        >
                          Confirm
                        </button>
                      </div>
                    ) : submission.rejectionReason ? (
                      <small>{submission.rejectionReason}</small>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {rejectingId ? (
        <div
          className="commercial-modal-backdrop"
          role="presentation"
          onMouseDown={() => setRejectingId(null)}
        >
          <section
            className="commercial-modal"
            role="dialog"
            aria-modal="true"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <header className="commercial-modal-header">
              <div>
                <h2>Reject Payment Submission</h2>
                <p>Explain why the submitted payment proof was rejected.</p>
              </div>
            </header>
            <div className="commercial-modal-body">
              <label className="commercial-field commercial-field--full">
                <span>Rejection reason *</span>
                <textarea
                  rows={4}
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                />
              </label>
            </div>
            <footer className="commercial-modal-footer">
              <button
                type="button"
                className="commercial-btn"
                disabled={saving}
                onClick={() => setRejectingId(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="commercial-btn commercial-btn-primary"
                disabled={saving || !reason.trim()}
                onClick={() => {
                  const submission = submissions.find((item) => item.id === rejectingId)
                  if (!submission) return
                  onReview(submission, {
                    status: 'rejected',
                    rejectionReason: reason.trim(),
                  })
                  setRejectingId(null)
                }}
              >
                Reject Submission
              </button>
            </footer>
          </section>
        </div>
      ) : null}
    </>
  )
}
