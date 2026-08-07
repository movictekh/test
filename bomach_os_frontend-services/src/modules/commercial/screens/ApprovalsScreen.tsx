import { approvalStatusClass, commercialMoney } from '../commercial.ui'
import type { ApprovalSummary, CommercialApproval } from '../types/commercial.types'

function formatOldestWaiting(days: number) {
  if (days <= 0) return '0d'
  return `${days}d`
}

export function ApprovalsScreen({
  summary,
  approvals,
  onOpen,
}: {
  summary: ApprovalSummary
  approvals: CommercialApproval[]
  onOpen: (approval: CommercialApproval) => void
}) {
  return (
    <main className="commercial-content">
      <section className="commercial-kgrid commercial-kgrid-4" aria-label="Approval summary">
        {[
          ['Pending approvals', summary.pending],
          ['High-value approvals', summary.highValue],
          ['Oldest waiting', formatOldestWaiting(summary.oldestWaitingDays)],
          ['Approval SLA', `${summary.approvalSlaPercent}%`],
        ].map(([label, value]) => (
          <article className="commercial-kpi" key={label}>
            <div className="commercial-kpi-label">{label}</div>
            <div className="commercial-kpi-value">{value}</div>
          </article>
        ))}
      </section>

      <section className="commercial-card">
        <header className="commercial-card-header">
          <div>
            <h2>Approval & Escalation Queue</h2>
            <p>Quotes, discounts, deliverables, milestones and closure</p>
          </div>
          <span className="commercial-count">{approvals.length} records</span>
        </header>

        <div className="commercial-table-wrap">
          <table className="commercial-table">
            <thead>
              <tr>
                <th>Approval</th>
                <th>Type</th>
                <th>Subject</th>
                <th>Requester</th>
                <th>Approver</th>
                <th>Amount</th>
                <th>Due</th>
                <th>Status</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {approvals.map((approval) => (
                <tr key={approval.id}>
                  <td>
                    <b>{approval.id}</b>
                    <small>{approval.entityId}</small>
                  </td>
                  <td>{approval.entityType}</td>
                  <td>{approval.subject}</td>
                  <td>{approval.requestedBy}</td>
                  <td>{approval.assignedTo}</td>
                  <td>
                    <b>{approval.amount > 0 ? commercialMoney.format(approval.amount) : '—'}</b>
                  </td>
                  <td>{approval.dueAt}</td>
                  <td>
                    <span className={`commercial-pill ${approvalStatusClass(approval.status)}`}>
                      {approval.status}
                    </span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="commercial-btn commercial-btn-small"
                      onClick={() => onOpen(approval)}
                    >
                      {approval.status === 'Pending' ? 'Review' : 'Open'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {approvals.length === 0 ? (
            <div className="commercial-empty" role="status">
              No approvals are waiting in the queue.
            </div>
          ) : null}
        </div>
      </section>
    </main>
  )
}
