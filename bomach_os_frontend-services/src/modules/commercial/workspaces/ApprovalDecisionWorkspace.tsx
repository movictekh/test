import { IconX } from '@tabler/icons-react'
import { useState } from 'react'

import { commercialMoney } from '../commercial.ui'
import type { CommercialApproval, DecideApprovalInput } from '../types/commercial.types'

export function ApprovalDecisionWorkspace({
  approval,
  saving,
  onClose,
  onDecide,
}: {
  approval: CommercialApproval
  saving: boolean
  onClose: () => void
  onDecide: (input: DecideApprovalInput) => void
}) {
  const [note, setNote] = useState('')

  return (
    <div className="commercial-modal-backdrop" onMouseDown={onClose}>
      <section className="commercial-modal" onMouseDown={(event) => event.stopPropagation()}>
        <header className="commercial-modal-header">
          <div>
            <h2>Approval — {approval.id}</h2>
            <p>
              {approval.entityType} {approval.entityId}
            </p>
          </div>
          <button type="button" className="commercial-modal-close" onClick={onClose}>
            <IconX size={16} />
          </button>
        </header>

        <div className="commercial-modal-body">
          <div className="commercial-info-grid">
            <div>
              <div className="commercial-kl">Client</div>
              <b>{approval.client}</b>
            </div>
            <div>
              <div className="commercial-kl">Amount</div>
              <b>{commercialMoney.format(approval.amount)}</b>
            </div>
            <div>
              <div className="commercial-kl">Requested by</div>
              <b>{approval.requestedBy}</b>
            </div>
            <div>
              <div className="commercial-kl">Assigned to</div>
              <b>{approval.assignedTo}</b>
            </div>
            <div className="commercial-info-full">
              <div className="commercial-kl">Reason</div>
              <p>{approval.reason}</p>
            </div>
          </div>

          <label className="commercial-field">
            <span>Decision note *</span>
            <textarea rows={4} value={note} onChange={(event) => setNote(event.target.value)} />
          </label>
        </div>

        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" onClick={onClose}>
            Close
          </button>
          {approval.status === 'Pending' ? (
            <>
              <button
                type="button"
                className="commercial-btn"
                disabled={saving || !note.trim()}
                onClick={() =>
                  onDecide({
                    approvalId: approval.id,
                    decision: 'reject',
                    note: note.trim(),
                  })
                }
              >
                Reject
              </button>
              <button
                type="button"
                className="commercial-btn commercial-btn-green"
                disabled={saving || !note.trim()}
                onClick={() =>
                  onDecide({
                    approvalId: approval.id,
                    decision: 'approve',
                    note: note.trim(),
                  })
                }
              >
                Approve
              </button>
            </>
          ) : null}
        </footer>
      </section>
    </div>
  )
}
