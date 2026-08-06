import { commercialMoney, quotationStatusClass } from '../commercial.ui'
import type { CommercialQuotation, QuotationSummary } from '../types/commercial.types'

export function QuotationsScreen({
  summary,
  quotations,
  onOpen,
}: {
  summary: QuotationSummary
  quotations: CommercialQuotation[]
  onOpen: (quotation: CommercialQuotation) => void
}) {
  return (
    <main className="commercial-content">
      <section className="commercial-kgrid commercial-kgrid-4" aria-label="Quotation summary">
        {[
          ['Draft quotes', summary.drafts],
          ['Awaiting approval', summary.awaitingApproval],
          ['Sent to clients', summary.sent],
          ['Acceptance rate', `${summary.acceptanceRate}%`],
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
            <h2>Quotations & Proposals</h2>
            <p>Version-controlled scope, pricing, terms and approvals</p>
          </div>
          <span className="commercial-count">{quotations.length} records</span>
        </header>

        <div className="commercial-table-wrap">
          <table className="commercial-table">
            <thead>
              <tr>
                <th>Quote</th>
                <th>Client</th>
                <th>Service</th>
                <th>Version</th>
                <th>Total</th>
                <th>Valid Until</th>
                <th>Status</th>
                <th>Owner</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {quotations.map((item) => (
                <tr key={item.id}>
                  <td>
                    <b>{item.id}</b>
                    <small>{item.createdAt}</small>
                  </td>
                  <td>{item.client}</td>
                  <td>{item.service}</td>
                  <td>v{item.version}</td>
                  <td>
                    <b>{commercialMoney.format(item.total)}</b>
                  </td>
                  <td>{item.validUntil}</td>
                  <td>
                    <span className={`commercial-pill ${quotationStatusClass(item.status)}`}>
                      {item.status}
                    </span>
                  </td>
                  <td>{item.owner}</td>
                  <td>
                    <button
                      type="button"
                      className="commercial-btn commercial-btn-small"
                      onClick={() => onOpen(item)}
                    >
                      Open
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {quotations.length === 0 ? (
            <div className="commercial-empty" role="status">
              No quotations yet. Build a quote from an eligible service request.
            </div>
          ) : null}
        </div>
      </section>
    </main>
  )
}
