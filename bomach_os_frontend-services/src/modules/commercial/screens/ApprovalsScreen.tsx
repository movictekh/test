import { IconChevronRight } from '@tabler/icons-react'

import { commercialMoney } from '../commercial.ui'
import type { ApprovalSummary, CommercialApproval } from '../types/commercial.types'

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
      <section className="commercial-kgrid">
        {[
          ['Pending', summary.pending, 'Awaiting decision'],
          ['High Value', summary.highValue, 'Above approval threshold'],
          ['Approved Today', summary.approvedToday, 'Completed decisions'],
          ['Rejected', summary.rejected, 'Returned to requester'],
        ].map(([label, value, note]) => (
          <article className="commercial-kpi" key={label}>
            <div className="commercial-kpi-label">{label}</div>
            <div className="commercial-kpi-value">{value}</div>
            <div className="commercial-kpi-note">{note}</div>
          </article>
        ))}
      </section>

      <section className="commercial-card">
        <header className="commercial-card-header">
          <div>
            <h2>Commercial Approval Queue</h2>
            <p>Quotations and invoices requiring accountable decisions</p>
          </div>
        </header>

        <div className="commercial-table-wrap">
          <table className="commercial-table">
            <thead>
              <tr>
                <th>Approval</th>
                <th>Type</th>
                <th>Record</th>
                <th>Client</th>
                <th>Reason</th>
                <th>Amount</th>
                <th>Assigned To</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {approvals.map((approval) => (
                <tr key={approval.id}>
                  <td>
                    <b>{approval.id}</b>
                    <small>{approval.requestedAt}</small>
                  </td>
                  <td>{approval.entityType}</td>
                  <td>{approval.entityId}</td>
                  <td>{approval.client}</td>
                  <td>{approval.reason}</td>
                  <td>
                    <b>{commercialMoney.format(approval.amount)}</b>
                  </td>
                  <td>{approval.assignedTo}</td>
                  <td>
                    <span className="commercial-pill commercial-pill-yellow">
                      {approval.status}
                    </span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="commercial-row-open"
                      onClick={() => onOpen(approval)}
                      aria-label={`Open ${approval.id}`}
                    >
                      <IconChevronRight size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {approvals.length === 0 ? (
            <div className="commercial-empty">No commercial approvals are waiting.</div>
          ) : null}
        </div>
      </section>
    </main>
  )
}
