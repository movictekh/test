import { IconFilePlus } from '@tabler/icons-react'
import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from '@tanstack/react-router'

import { useAuth } from '@/app/auth'
import { presentError } from '@/shared/errors'
import { formatCurrency } from '@/shared/lib/formatters'
import { cn } from '@/shared/lib/cn'
import { DashboardSkeleton, ErrorState } from '@/shared/ui'
import '@/modules/service-administration/styles/service-administration.css'

import { dashboardQueries } from '../api/dashboard.queries'
import type {
  DashboardAttentionItem,
  DashboardExecutiveAlert,
  DashboardHealthMetric,
  DashboardMetric,
  DashboardPipelineStage,
  DashboardRevenueByDivision,
  DashboardActivityItem,
} from '../types/dashboard.types'
import '../styles/command-center.css'

function formatMetricValue(metric: DashboardMetric) {
  if (metric.valueFormat === 'currency') return formatCurrency(metric.value)
  if (metric.valueFormat === 'percent') return `${metric.value}%`
  return metric.value.toLocaleString('en-NG')
}

function statusPillClass(status?: string) {
  const value = (status ?? '').toLowerCase()
  if (
    /paid|accepted|completed|approved|active|done|available|closed|converted|verified|quoted/.test(
      value,
    )
  ) {
    return 'command-center-pill-blue'
  }
  if (
    /overdue|rejected|sold|action required|site assessment|under review|awaiting|pending|reserved|inspection/.test(
      value,
    )
  ) {
    return 'command-center-pill-yellow'
  }
  if (/draft|new|to do|hold|unpaid/.test(value)) {
    return 'command-center-pill-gray'
  }
  return 'command-center-pill-blue'
}

function alertTitle(alert: DashboardExecutiveAlert) {
  if (alert.value === undefined) return alert.title
  if (alert.valueFormat === 'currency') return `${formatCurrency(alert.value)} ${alert.title}`
  if (alert.valueFormat === 'percent') return `${alert.title}`
  return `${alert.value} ${alert.title}`
}

function alertNoticeClass(severity: DashboardExecutiveAlert['severity']) {
  if (severity === 'danger') return 'command-center-notice-red'
  if (severity === 'warning') return 'command-center-notice-yellow'
  if (severity === 'success') return 'command-center-notice-green'
  return 'command-center-notice-blue'
}

function healthBarColor(value: number) {
  if (value < 80) return 'var(--cc-r)'
  if (value < 90) return 'var(--cc-y)'
  return 'var(--cc-g)'
}

function defaultLifecycle(): DashboardPipelineStage[] {
  return [
    { key: 'request', label: 'Request', count: 0, state: 'done' },
    { key: 'assessment', label: 'Assessment', count: 0, state: 'done' },
    { key: 'quotation', label: 'Quotation', count: 0, state: 'done' },
    { key: 'approval', label: 'Approval', count: 0, state: 'active' },
    { key: 'invoice-payment', label: 'Invoice & Payment', count: 0, state: 'pending' },
    { key: 'service-order', label: 'Service Order', count: 0, state: 'pending' },
    { key: 'fulfillment', label: 'Fulfillment', count: 0, state: 'pending' },
    { key: 'acceptance', label: 'Acceptance', count: 0, state: 'pending' },
  ]
}

function KpiGrid({ metrics }: { metrics: DashboardMetric[] }) {
  return (
    <div className="command-center-kpis">
      {metrics.slice(0, 5).map((metric) => (
        <div key={metric.key} className="command-center-kpi">
          <div className="command-center-kpi-label">{metric.label}</div>
          <div className="command-center-kpi-value">{formatMetricValue(metric)}</div>
          <div className="command-center-kpi-sub">
            {metric.trend?.direction === 'up' ? (
              <span className="command-center-up">{metric.trend.label}</span>
            ) : metric.trend?.direction === 'down' ? (
              <span className="command-center-down">{metric.trend.label}</span>
            ) : (
              metric.description
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function LifecycleCard({ stages }: { stages: DashboardPipelineStage[] }) {
  const items = stages.length >= 8 ? stages : defaultLifecycle()

  return (
    <section className="command-center-card">
      <div className="command-center-card-header">
        <div>
          <div className="command-center-card-title">End-to-end service lifecycle</div>
          <div className="command-center-card-subtitle">Commercial and operational handoff</div>
        </div>
        <span className="command-center-pill command-center-pill-blue">Standard journey</span>
      </div>
      <div className="command-center-life">
        {items.map((stage, index) => {
          const state = stage.state ?? 'pending'
          const stateLabel =
            state === 'done' ? 'Completed' : state === 'active' ? 'In progress' : 'Pending'
          return (
            <div
              key={stage.key}
              className={cn(
                'command-center-step',
                state === 'done' && 'command-center-step--done',
                state === 'active' && 'command-center-step--active',
              )}
            >
              <small>{String(index + 1).padStart(2, '0')}</small>
              <b>{stage.label}</b>
              <span>{stateLabel}</span>
            </div>
          )
        })}
      </div>
    </section>
  )
}

function RequestsTable({ items }: { items: DashboardAttentionItem[] }) {
  const navigate = useNavigate()

  return (
    <section className="command-center-card">
      <div className="command-center-card-header">
        <div>
          <div className="command-center-card-title">Requests requiring action</div>
          <div className="command-center-card-subtitle">Prioritized by SLA, value and urgency</div>
        </div>
        <Link
          to="/app/$section"
          params={{ section: 'service-requests' }}
          className="command-center-btn command-center-btn-small"
        >
          View all
        </Link>
      </div>
      <div className="command-center-table-wrap">
        <table className="command-center-table">
          <thead>
            <tr>
              <th>Request</th>
              <th>Client</th>
              <th>Service</th>
              <th>Status</th>
              <th>Owner</th>
              <th>Next action</th>
            </tr>
          </thead>
          <tbody>
            {items.slice(0, 5).map((item) => (
              <tr
                key={item.id}
                onClick={() => {
                  if (!item.destination) return
                  void navigate({
                    to: '/app/$section',
                    params: { section: item.destination.section },
                  })
                }}
              >
                <td>
                  <b>{item.requestNumber ?? item.recordNumber ?? item.id}</b>
                  <div className="command-center-row-sub">{item.createdLabel ?? '—'}</div>
                </td>
                <td>{item.client ?? '—'}</td>
                <td>{item.service ?? '—'}</td>
                <td>
                  <span className={`command-center-pill ${statusPillClass(item.statusLabel)}`}>
                    {item.statusLabel ?? item.severity}
                  </span>
                </td>
                <td>{item.owner ?? '—'}</td>
                <td>{item.nextAction ?? item.description ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function ExecutiveAlertsCard({ alerts }: { alerts: DashboardExecutiveAlert[] }) {
  return (
    <section className="command-center-card">
      <div className="command-center-card-header">
        <div className="command-center-card-title">Executive alerts</div>
      </div>
      {alerts.map((alert) => (
        <div key={alert.id} className={`command-center-notice ${alertNoticeClass(alert.severity)}`}>
          <b>{alertTitle(alert)}</b>
          <br />
          {alert.description}
        </div>
      ))}
    </section>
  )
}

function OperationsHealthCard({ metrics }: { metrics: DashboardHealthMetric[] }) {
  return (
    <section className="command-center-card">
      <div className="command-center-card-header">
        <div className="command-center-card-title">Operations health</div>
      </div>
      {metrics.map((metric) => (
        <div key={metric.key} className="command-center-metric">
          <label>{metric.label}</label>
          <div className="command-center-progress" style={{ width: 90 }}>
            <i style={{ width: `${metric.value}%`, background: healthBarColor(metric.value) }} />
          </div>
          <strong>{metric.value}%</strong>
        </div>
      ))}
    </section>
  )
}

function RevenueByDivisionCard({ rows }: { rows: DashboardRevenueByDivision[] }) {
  const max = Math.max(...rows.map((row) => row.verifiedRevenue), 1)

  return (
    <section className="command-center-card">
      <div className="command-center-card-header">
        <div>
          <div className="command-center-card-title">Revenue by division</div>
          <div className="command-center-card-subtitle">Based on verified payments</div>
        </div>
      </div>
      {rows.map((row) => (
        <div key={row.id} className="command-center-metric">
          <label>{row.division}</label>
          <div className="command-center-progress" style={{ flex: 1 }}>
            <i style={{ width: `${Math.max(8, (row.verifiedRevenue / max) * 100)}%` }} />
          </div>
          <strong>{formatCurrency(row.verifiedRevenue)}</strong>
        </div>
      ))}
    </section>
  )
}

function RecentActivityCard({ items }: { items: DashboardActivityItem[] }) {
  return (
    <section className="command-center-card">
      <div className="command-center-card-header">
        <div>
          <div className="command-center-card-title">Recent system activity</div>
          <div className="command-center-card-subtitle">Permanent audit history</div>
        </div>
        <Link
          to="/app/$section"
          params={{ section: 'audit-log' }}
          className="command-center-btn command-center-btn-small"
        >
          Full log
        </Link>
      </div>
      <div className="command-center-timeline">
        {items.slice(0, 5).map((item) => (
          <div key={item.id} className="command-center-tl">
            <b>{item.title}</b>
            <p>{item.actor ?? 'System'}</p>
            <time>{new Date(item.occurredAt).toLocaleString('en-NG')}</time>
          </div>
        ))}
      </div>
    </section>
  )
}

export function OperationsDashboardPage() {
  const { user } = useAuth()
  const userId = user?.id ?? ''

  const summaryQuery = useQuery({ ...dashboardQueries.summary(userId), enabled: Boolean(userId) })
  const activityQuery = useQuery(dashboardQueries.recentActivity())

  if (summaryQuery.isPending) return (
      <div className="min-h-0 flex-1 overflow-y-auto">
        <DashboardSkeleton />
      </div>
    )
  if (summaryQuery.isError) {
    const error = presentError(summaryQuery.error, 'page-load')
    return (
      <div className="min-h-0 flex-1 overflow-y-auto">
        <ErrorState
          title={error.title}
          description={error.message}
          onRetry={() => void summaryQuery.refetch()}
        />
      </div>
    )
  }

  const summary = summaryQuery.data
  const activity = activityQuery.data ?? []

  return (
    <div className="command-center">
      <section className="command-center-toolbar">
        <div className="command-center-toolbar-title">
          Service Command Center
          <small>Services / Executive overview</small>
        </div>
        <Link
          to="/app/$section"
          params={{ section: 'service-requests' }}
          className="command-center-btn"
        >
          <IconFilePlus size={14} />
          New Request
        </Link>
      </section>

      <main className="command-center-content">
        <KpiGrid metrics={summary.metrics} />

        <div className="command-center-g21">
          <div className="command-center-g21-main">
            <LifecycleCard stages={summary.pipeline} />
            <RequestsTable items={summary.attentionItems} />
          </div>
          <div className="command-center-g21-side">
            <ExecutiveAlertsCard alerts={summary.executiveAlerts} />
            <OperationsHealthCard metrics={summary.operationsHealth} />
          </div>
        </div>

        <div className="command-center-g2">
          <RevenueByDivisionCard rows={summary.revenueByDivision} />
          {activityQuery.isPending ? (
            <section className="command-center-card">
              <div className="command-center-card-title">Recent system activity</div>
              <div className="command-center-card-subtitle">Loading audit history…</div>
            </section>
          ) : activityQuery.isError ? (
            <section className="command-center-card">
              <div className="command-center-card-title">Recent system activity</div>
              <div className="command-center-card-subtitle">
                {presentError(activityQuery.error, 'section-load').message}
              </div>
            </section>
          ) : (
            <RecentActivityCard items={activity} />
          )}
        </div>
      </main>
    </div>
  )
}
