import { IconChevronRight, IconSearch } from '@tabler/icons-react'
import { useMemo, useState } from 'react'

import { commercialMoney } from '../commercial.ui'
import type { CommercialInvoice, InvoiceSummary } from '../types/commercial.types'

function invoiceStatusClass(status: string) {
  if (status === 'Paid') return 'commercial-pill-green'
  if (status === 'Overdue' || status === 'Cancelled') {
    return 'commercial-pill-red'
  }
  if (status === 'Part Paid') return 'commercial-pill-yellow'
  if (status === 'Draft') return 'commercial-pill-gray'
  return 'commercial-pill-blue'
}

export function InvoicesPaymentsScreen({
  summary,
  invoices,
  onOpen,
}: {
  summary: InvoiceSummary
  invoices: CommercialInvoice[]
  onOpen: (invoice: CommercialInvoice) => void
}) {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('All statuses')

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase()

    return invoices.filter((invoice) => {
      const matchesSearch =
        !needle ||
        [invoice.id, invoice.quotationId, invoice.client, invoice.service].some((value) =>
          value.toLowerCase().includes(needle),
        )

      return matchesSearch && (status === 'All statuses' || invoice.status === status)
    })
  }, [invoices, search, status])

  return (
    <main className="commercial-content">
      <section className="commercial-kgrid commercial-kgrid-5">
        {[
          ['Invoices', summary.total, 'All billing records'],
          ['Outstanding', commercialMoney.format(summary.outstanding), 'Open balance'],
          ['Overdue', summary.overdue, 'Past due date'],
          ['Collected', commercialMoney.format(summary.collected), 'Payments received'],
          ['Collection Rate', `${summary.collectionRate}%`, 'Paid value ratio'],
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
            <h2>Invoices & Payments Register</h2>
            <p>Billing, balances, due dates and payment allocation</p>
          </div>
          <span className="commercial-record-count">{filtered.length} records</span>
        </header>

        <div className="commercial-filter-row">
          <label className="commercial-search">
            <IconSearch size={14} />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search invoice, quotation, client or service"
            />
          </label>
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option>All statuses</option>
            {Array.from(new Set(invoices.map((invoice) => invoice.status))).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </div>

        <div className="commercial-table-wrap">
          <table className="commercial-table">
            <thead>
              <tr>
                <th>Invoice</th>
                <th>Quotation</th>
                <th>Client</th>
                <th>Service</th>
                <th>Status</th>
                <th>Total</th>
                <th>Paid</th>
                <th>Balance</th>
                <th>Due</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filtered.map((invoice) => (
                <tr key={invoice.id}>
                  <td>
                    <b>{invoice.id}</b>
                    <small>{invoice.createdAt}</small>
                  </td>
                  <td>{invoice.quotationId}</td>
                  <td>{invoice.client}</td>
                  <td>
                    <b>{invoice.service}</b>
                    <small>{invoice.branch}</small>
                  </td>
                  <td>
                    <span className={`commercial-pill ${invoiceStatusClass(invoice.status)}`}>
                      {invoice.status}
                    </span>
                  </td>
                  <td>{commercialMoney.format(invoice.total)}</td>
                  <td>{commercialMoney.format(invoice.amountPaid)}</td>
                  <td>
                    <b>{commercialMoney.format(invoice.balance)}</b>
                  </td>
                  <td>{invoice.dueAt}</td>
                  <td>
                    <button
                      type="button"
                      className="commercial-row-open"
                      onClick={() => onOpen(invoice)}
                      aria-label={`Open ${invoice.id}`}
                    >
                      <IconChevronRight size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 ? (
            <div className="commercial-empty">No invoices match the selected filters.</div>
          ) : null}
        </div>
      </section>
    </main>
  )
}
