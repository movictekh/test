import { IconX } from '@tabler/icons-react'
import type { Deliverable } from '../types/fulfillment.types'

export function DeliverableDetailWorkspace({
  deliverable,
  saving,
  canApprove,
  onClose,
  onApprove,
  onReject,
}: {
  deliverable: Deliverable
  saving: boolean
  canApprove: boolean
  onClose: () => void
  onApprove: () => void
  onReject: () => void
}) {
  return (
    <div className="fulfillment-modal-backdrop" onMouseDown={onClose}>
      <section className="fulfillment-modal" onMouseDown={(e) => e.stopPropagation()}>
        <header className="fulfillment-modal-header">
          <h2>{deliverable.title}</h2>
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
          <div className="fulfillment-grid-2">
            <div>
              <div className="fulfillment-kl">Order</div>
              <b>{deliverable.orderId}</b>
              <div className="fulfillment-kl fulfillment-top-gap">Type / Version</div>
              <b>
                {deliverable.type} · {deliverable.version}
              </b>
              <div className="fulfillment-top-gap">
                <span className="fulfillment-pill fulfillment-pill-blue">{deliverable.status}</span>
              </div>
            </div>
            <div className="fulfillment-notice fulfillment-notice-blue">
              <b>Document Controls</b>
              <br />
              Version history, reviewer comments, approval record, client visibility and download
              audit are retained.
              {deliverable.fileName ? (
                <>
                  <br />
                  <strong>{deliverable.fileName}</strong>
                </>
              ) : null}
            </div>
          </div>
        </div>
        <footer className="fulfillment-modal-footer">
          <button type="button" className="fulfillment-btn" onClick={onClose}>
            Close
          </button>
          {deliverable.status === 'Under Review' && canApprove ? (
            <>
              <button
                type="button"
                className="fulfillment-btn"
                disabled={saving}
                onClick={onReject}
              >
                Reject
              </button>
              <button
                type="button"
                className="fulfillment-btn fulfillment-btn-green"
                disabled={saving}
                onClick={onApprove}
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
