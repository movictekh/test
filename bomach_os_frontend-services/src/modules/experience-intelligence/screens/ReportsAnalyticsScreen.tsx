import { formatCurrency } from '@/shared/lib/formatters'

import { downloadCsv } from '../lib/csv'
import type { ReportSnapshot } from '../types/experience-intelligence.types'

export function ReportsAnalyticsScreen({ report }: { report: ReportSnapshot }) {
  return (
    <main className="experience-content">
      <div className="experience-kpi-grid">
        <article className="experience-kpi-card">
          <div>Quote-to-order conversion</div>
          <strong>{report.quoteToOrderConversion}%</strong>
        </article>
        <article className="experience-kpi-card">
          <div>Average response time</div>
          <strong>{report.averageResponseMinutes}m</strong>
        </article>
        <article className="experience-kpi-card">
          <div>Gross service margin</div>
          <strong>{report.grossServiceMargin}%</strong>
        </article>
        <article className="experience-kpi-card">
          <div>On-time delivery</div>
          <strong>{report.onTimeDelivery}%</strong>
        </article>
      </div>

      <div className="experience-grid-2">
        <section className="experience-card">
          <header className="experience-card-header">
            <div className="experience-card-title">Service Performance</div>
            <button
              type="button"
              className="experience-btn experience-btn-small"
              onClick={() =>
                downloadCsv(
                  'service-performance.csv',
                  ['Service', 'Average completion', 'Order value'],
                  report.services.map((item) => [
                    item.service,
                    `${item.averageCompletion}%`,
                    item.orderValue,
                  ]),
                )
              }
            >
              Export CSV
            </button>
          </header>

          {report.services.map((item) => (
            <div className="experience-metric" key={item.service}>
              <label>
                <b>{item.service}</b>
                <span>{item.averageCompletion}% average completion</span>
              </label>
              <div className="experience-progress">
                <i style={{ width: `${item.averageCompletion}%` }} />
              </div>
              <strong>{formatCurrency(item.orderValue)}</strong>
            </div>
          ))}

          {report.services.length === 0 ? (
            <div className="experience-empty">No service-order performance data.</div>
          ) : null}
        </section>

        <section className="experience-card">
          <header className="experience-card-header">
            <div className="experience-card-title">Branch Performance</div>
          </header>

          <div className="experience-table-wrap">
            <table className="experience-table experience-branch-table">
              <thead>
                <tr>
                  <th>Branch</th>
                  <th>Requests</th>
                  <th>Active Orders</th>
                  <th>Revenue</th>
                  <th>SLA</th>
                  <th>CSAT</th>
                </tr>
              </thead>
              <tbody>
                {report.branches.map((item) => (
                  <tr key={item.branch}>
                    <td>
                      <b>{item.branch}</b>
                    </td>
                    <td>{item.requests}</td>
                    <td>{item.activeOrders}</td>
                    <td>{formatCurrency(item.revenue)}</td>
                    <td>{item.sla}%</td>
                    <td>{item.csat}%</td>
                  </tr>
                ))}
                {report.branches.length === 0 ? (
                  <tr>
                    <td colSpan={6}>
                      <div className="experience-empty">No branch data.</div>
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  )
}
