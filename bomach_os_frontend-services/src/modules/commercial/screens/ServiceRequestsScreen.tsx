import { IconSearch } from '@tabler/icons-react'
import { useMemo, useState } from 'react'

import { commercialMoney, requestStatusClass } from '../commercial.ui'
import type { CommercialServiceRequest, CommercialSummary } from '../types/commercial.types'

export function ServiceRequestsScreen({
  summary,
  requests,
  onOpenRequest,
}: {
  summary: CommercialSummary
  requests: CommercialServiceRequest[]
  onOpenRequest: (request: CommercialServiceRequest) => void
}) {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('All statuses')
  const [branch, setBranch] = useState('All branches')
  const [service, setService] = useState('All services')

  const statuses = useMemo(
    () => ['All statuses', ...new Set(requests.map((request) => request.status))],
    [requests],
  )
  const branches = useMemo(
    () => ['All branches', ...new Set(requests.map((request) => request.branch))],
    [requests],
  )
  const services = useMemo(
    () => ['All services', ...new Set(requests.map((request) => request.service))],
    [requests],
  )

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase()

    return requests.filter((request) => {
      const matchesSearch =
        !needle ||
        [request.id, request.client, request.service, request.owner, request.nextAction].some(
          (value) => value.toLowerCase().includes(needle),
        )

      return (
        matchesSearch &&
        (status === 'All statuses' || request.status === status) &&
        (branch === 'All branches' || request.branch === branch) &&
        (service === 'All services' || request.service === service)
      )
    })
  }, [branch, requests, search, service, status])

  return (
    <main className="commercial-content">
      <section className="commercial-kgrid" aria-label="Request summary">
        {[
          ['New / unreviewed', summary.newRequests, 'Require assignment'],
          ['Site assessment required', summary.underReview, 'Assessment in progress'],
          ['Awaiting client information', summary.awaitingQuotation, 'Commercial action'],
          ['High Priority', summary.highPriority, 'High and urgent'],
          ['Total Requests', summary.total, 'All commercial requests'],
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
            <h2>Service Request Register</h2>
            <p>Client demand from intake through quotation readiness</p>
          </div>
          <span className="commercial-count">{filtered.length} records</span>
        </header>

        <div className="commercial-filters">
          <label className="commercial-search">
            <IconSearch size={14} aria-hidden="true" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search request, client, service or owner"
              aria-label="Search service requests"
            />
          </label>

          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            {statuses.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>

          <select value={branch} onChange={(event) => setBranch(event.target.value)}>
            {branches.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>

          <select value={service} onChange={(event) => setService(event.target.value)}>
            {services.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </div>

        {filtered.length === 0 ? (
          <div className="commercial-empty" role="status">
            No service requests match the selected filters.
          </div>
        ) : (
          <div className="commercial-table-wrap">
            <table className="commercial-table">
              <thead>
                <tr>
                  <th>Request</th>
                  <th>Client</th>
                  <th>Service</th>
                  <th>Source</th>
                  <th>Estimate</th>
                  <th>Status</th>
                  <th>Owner</th>
                  <th>Next</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((request) => (
                  <tr key={request.id}>
                    <td>
                      <b>{request.id}</b>
                      <small>
                        {request.createdAt} · {request.branch}
                      </small>
                    </td>
                    <td>
                      <b>{request.client}</b>
                      <small>{request.clientType}</small>
                    </td>
                    <td>
                      <b>{request.service}</b>
                      <small>{request.division}</small>
                    </td>
                    <td>{request.source}</td>
                    <td>
                      <b>{commercialMoney.format(request.estimate || request.budget)}</b>
                    </td>
                    <td>
                      <span className={`commercial-pill ${requestStatusClass(request.status)}`}>
                        {request.status}
                      </span>
                    </td>
                    <td>{request.owner}</td>
                    <td>{request.nextAction}</td>
                    <td>
                      <button
                        type="button"
                        className="commercial-btn commercial-btn-small"
                        onClick={() => onOpenRequest(request)}
                      >
                        Open
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  )
}
