import { commercialMoney, invoiceStatusClass } from '../commercial.ui'
import type { CommercialInvoice, InvoiceSummary } from '../types/commercial.types'

export function InvoicesPaymentsScreen({
  summary,
  invoices,
  onOpen,
}: {
  summary: InvoiceSummary
  invoices: CommercialInvoice[]
  onOpen: (invoice: CommercialInvoice) => void
}) {
  return (
    <main className="commercial-content">
      <section className="commercial-kgrid commercial-kgrid-4" aria-label="Invoice summary">
        {[
          ['Total invoiced', commercialMoney.format(summary.totalInvoiced)],
          ['Paid', commercialMoney.format(summary.paid)],
          ['Outstanding', commercialMoney.format(summary.outstanding)],
          ['Overdue', summary.overdue],
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
            <h2>Invoices, Payment Schedules & Receipts</h2>
            <p>Orders activate after the required payment threshold is met</p>
          </div>
          <span className="commercial-count">{invoices.length} records</span>
        </header>

        <div className="commercial-table-wrap">
          <table className="commercial-table">
            <thead>
              <tr>
                <th>Invoice</th>
                <th>Client</th>
                <th>Service</th>
                <th>Total</th>
                <th>Paid</th>
                <th>Balance</th>
                <th>Due</th>
                <th>Status</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {invoices.map((invoice) => (
                <tr key={invoice.id}>
                  <td>
                    <b>{invoice.id}</b>
                    <small>{invoice.schedule}</small>
                  </td>
                  <td>{invoice.client}</td>
                  <td>{invoice.service}</td>
                  <td>{commercialMoney.format(invoice.total)}</td>
                  <td>{commercialMoney.format(invoice.amountPaid)}</td>
                  <td>
                    <b>{commercialMoney.format(invoice.balance)}</b>
                  </td>
                  <td>{invoice.dueAt}</td>
                  <td>
                    <span className={`commercial-pill ${invoiceStatusClass(invoice.status)}`}>
                      {invoice.status}
                    </span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="commercial-btn commercial-btn-small"
                      onClick={() => onOpen(invoice)}
                    >
                      Open
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {invoices.length === 0 ? (
            <div className="commercial-empty" role="status">
              No invoices yet. Create an invoice from an accepted quotation.
            </div>
          ) : null}
        </div>
      </section>
    </main>
  )
}
