import { IconX } from '@tabler/icons-react'
import { useState } from 'react'
import { useToast } from '@/shared/ui'

import { commercialMoney, quotationStatusClass } from '../commercial.ui'
import type { CommercialQuotation, UpdateQuotationInput } from '../types/commercial.types'
import { quotationActionAllowed } from './quotation-workflow.rules'

export function QuotationDetailWorkspace({
  quotation,
  saving,
  onClose,
  onUpdate,
  onCreateInvoice,
}: {
  quotation: CommercialQuotation
  saving: boolean
  onClose: () => void
  onUpdate: (id: string, input: UpdateQuotationInput) => void
  onCreateInvoice?: (quotationId: string) => void
}) {
  const toast = useToast()
  const [decisionNote, setDecisionNote] = useState('')
  const canSubmitApproval = quotationActionAllowed(quotation.status, 'submit-approval')
  const canSend = quotationActionAllowed(quotation.status, 'send')
  const canAccept = quotationActionAllowed(quotation.status, 'accept')
  const canReject = quotationActionAllowed(quotation.status, 'reject')

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="commercial-modal commercial-modal--xl"
        role="dialog"
        aria-modal="true"
        aria-label={`Quotation ${quotation.id}`}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Quotation File — {quotation.id}</h2>
            <p>
              {quotation.client} · {quotation.service} · v{quotation.version}
            </p>
          </div>
          <div className="commercial-modal-header-meta">
            <span className={`commercial-pill ${quotationStatusClass(quotation.status)}`}>
              {quotation.status}
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
            <h3>Commercial offer</h3>
            <p className="commercial-form-note">
              Request {quotation.requestId} · Valid until {quotation.validUntil}
            </p>
            <div className="commercial-info-grid">
              <div>
                <div className="commercial-kl">Client</div>
                <b>{quotation.client}</b>
              </div>
              <div>
                <div className="commercial-kl">Service</div>
                <b>{quotation.service}</b>
              </div>
              <div>
                <div className="commercial-kl">Branch</div>
                <b>{quotation.branch}</b>
              </div>
              <div>
                <div className="commercial-kl">Owner</div>
                <b>{quotation.owner}</b>
              </div>
              <div>
                <div className="commercial-kl">Deposit</div>
                <b>{quotation.depositPercent}%</b>
              </div>
              <div>
                <div className="commercial-kl">Approval route</div>
                <b>{quotation.approvalRoute || '—'}</b>
              </div>
            </div>
          </section>

          <section className="commercial-form-section">
            <h3>Pricing breakdown</h3>
            <p className="commercial-form-note">Subtotal, adjustments and offer total</p>
            <div className="commercial-quote-pricing-layout">
              <div className="commercial-quote-breakdown">
                <div>
                  <span>Subtotal</span>
                  <b>{commercialMoney.format(quotation.subtotal)}</b>
                </div>
                <div>
                  <span>Discount</span>
                  <b>-{commercialMoney.format(quotation.discountAmount)}</b>
                </div>
                <div>
                  <span>Tax ({quotation.taxPercent}%)</span>
                  <b>{commercialMoney.format(quotation.taxAmount)}</b>
                </div>
                <div className="commercial-quote-breakdown-total">
                  <span>Offer total</span>
                  <b>{commercialMoney.format(quotation.total)}</b>
                </div>
              </div>
              <article className="commercial-quote-value-card">
                <div className="commercial-kpi-label">Total value</div>
                <div className="commercial-kpi-value">
                  {commercialMoney.format(quotation.total)}
                </div>
                <div className="commercial-kpi-note">
                  Version {quotation.version} · Valid until {quotation.validUntil}
                </div>
              </article>
            </div>
          </section>

          <section className="commercial-form-section">
            <h3>Scope and terms</h3>
            <div className="commercial-info-grid">
              {quotation.notes ? (
                <div className="commercial-info-full">
                  <div className="commercial-kl">Scope</div>
                  <p>{quotation.notes}</p>
                </div>
              ) : null}
              {quotation.paymentTerms ? (
                <div className="commercial-info-full">
                  <div className="commercial-kl">Payment schedule & terms</div>
                  <p>{quotation.paymentTerms}</p>
                </div>
              ) : null}
              {quotation.deliveryTerms ? (
                <div className="commercial-info-full">
                  <div className="commercial-kl">Delivery terms</div>
                  <p>{quotation.deliveryTerms}</p>
                </div>
              ) : null}
            </div>
          </section>
          <section className="commercial-form-section">
            <h3>Activity & audit trail</h3>
            <div className="commercial-timeline-list">
              {[...quotation.activities].reverse().map((activity) => (
                <article key={activity.id} className="commercial-tl">
                  <b>{activity.title}</b>
                  <p>
                    {activity.description}
                    <br />
                    <strong>{activity.actor}</strong>
                  </p>
                  <time>{new Date(activity.at).toLocaleString('en-GB')}</time>
                </article>
              ))}
            </div>
          </section>
        </div>

        <footer className="commercial-modal-footer">
          <div className="commercial-modal-footer-start">
            <button type="button" className="commercial-btn" onClick={onClose}>
              Close
            </button>
          </div>
          <div className="commercial-modal-footer-actions">
            {canSubmitApproval ? (
              <button
                type="button"
                className="commercial-btn commercial-btn-primary"
                disabled={saving}
                onClick={() => onUpdate(quotation.id, { action: 'submit-approval' })}
              >
                {saving ? 'Submitting...' : 'Submit Approval'}
              </button>
            ) : null}
            {quotation.status === 'Awaiting Approval' ? (
              <span className="commercial-form-note">
                Approval is controlled from the Commercial Approval Queue.
              </span>
            ) : null}
            {canSend ? (
              <button
                type="button"
                className="commercial-btn commercial-btn-primary"
                disabled={saving}
                onClick={() => onUpdate(quotation.id, { action: 'send' })}
              >
                {saving ? 'Sending...' : 'Send to Client'}
              </button>
            ) : null}
            {canAccept || canReject ? (
              <div className="commercial-decision-actions">
                <label className="commercial-field">
                  <span>Client decision note</span>
                  <textarea
                    rows={3}
                    value={decisionNote}
                    onChange={(event) => setDecisionNote(event.target.value)}
                    placeholder="Required for rejection"
                  />
                </label>
                {canReject ? (
                  <button
                    type="button"
                    className="commercial-btn"
                    disabled={saving || !decisionNote.trim()}
                    onClick={() =>
                      onUpdate(quotation.id, {
                        action: 'reject',
                        decisionNote: decisionNote.trim(),
                      })
                    }
                  >
                    Mark Rejected
                  </button>
                ) : null}
                {canAccept ? (
                  <button
                    type="button"
                    className="commercial-btn commercial-btn-green"
                    disabled={saving}
                    onClick={() =>
                      onUpdate(quotation.id, {
                        action: 'accept',
                        decisionNote: decisionNote.trim(),
                      })
                    }
                  >
                    {saving ? 'Saving...' : 'Mark Accepted'}
                  </button>
                ) : null}
              </div>
            ) : null}
            {quotation.status === 'Accepted' ? (
              <button
                type="button"
                className="commercial-btn commercial-btn-primary"
                disabled={saving}
                onClick={() => {
                  if (onCreateInvoice) onCreateInvoice(quotation.id)
                  else {
                    toast.success('Invoice builder opens next', {
                      description: `Invoice draft will use ${quotation.id}.`,
                    })
                    onClose()
                  }
                }}
              >
                Create Invoice
              </button>
            ) : null}
          </div>
        </footer>
      </section>
    </div>
  )
}
