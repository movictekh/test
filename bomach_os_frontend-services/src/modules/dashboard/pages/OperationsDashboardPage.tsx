import { IconFilePlus } from '@tabler/icons-react'
import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from '@tanstack/react-router'

import { presentError } from '@/shared/errors'
import { formatCurrency } from '@/shared/lib/formatters'
import { cn } from '@/shared/lib/cn'
import { DashboardSkeleton, ErrorState, EmptyState } from '@/shared/ui'
import '@/modules/service-administration/styles/service-administration.css'

import { dashboardQueries } from '../api/dashboard.queries'
import type {
  DashboardAttentionItem,
  DashboardExecutiveAlert,
  DashboardMetric,
  DashboardPipelineStage,
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
  const items = stages

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

function ActionItemsCard({ items }: { items: DashboardAttentionItem[] }) {
  const navigate = useNavigate()

  return (
    <section className="command-center-card">
      <div className="command-center-card-header">
        <div>
          <div className="command-center-card-title">My action items</div>
          <div className="command-center-card-subtitle">
            Work the backend says currently requires your attention
          </div>
        </div>
      </div>

      <div className="command-center-table-wrap">
        <table className="command-center-table">
          <thead>
            <tr>
              <th>Item</th>
              <th>Type</th>
              <th>Priority</th>
              <th>Due</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {items.slice(0, 8).map((item) => (
              <tr
                key={item.id}
                onClick={() => {
                  if (!item.destination) return
                  void navigate({
                    to: '/app/$section',
                    params: { section: item.destination.section },
                    search: item.destination.search ?? {},
                  })
                }}
              >
                <td>
                  <b>{item.title}</b>
                </td>
                <td>{item.recordType}</td>
                <td>
                  <span className={`command-center-pill ${statusPillClass(item.priority)}`}>
                    {item.priority ?? item.severity}
                  </span>
                </td>
                <td>{item.dueLabel ?? '—'}</td>
                <td>{item.description || '—'}</td>
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

function RecentActivityCard({ items }: { items: DashboardActivityItem[] }) {
  const navigate = useNavigate()

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
          <div
            key={item.id}
            className="command-center-tl"
            role={item.destination ? 'button' : undefined}
            tabIndex={item.destination ? 0 : undefined}
            onClick={() => {
              if (!item.destination) return
              void navigate({
                to: '/app/$section',
                params: { section: item.destination.section },
                search: item.destination.search ?? {},
              })
            }}
            onKeyDown={(event) => {
              if (!item.destination || (event.key !== 'Enter' && event.key !== ' ')) return
              event.preventDefault()
              void navigate({
                to: '/app/$section',
                params: { section: item.destination.section },
                search: item.destination.search ?? {},
              })
            }}
          >
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
  const financialsQuery = useQuery(dashboardQueries.financials())
  const approvalsQuery = useQuery(dashboardQueries.pendingApprovals())
  const pipelineQuery = useQuery(dashboardQueries.pipeline())
  const actionItemsQuery = useQuery(dashboardQueries.actionItems())
  const activityQuery = useQuery(dashboardQueries.activity())

  const allPending =
    financialsQuery.isPending &&
    approvalsQuery.isPending &&
    pipelineQuery.isPending &&
    actionItemsQuery.isPending &&
    activityQuery.isPending

  if (allPending) {
    return (
      <div className="min-h-0 flex-1 overflow-y-auto">
        <DashboardSkeleton />
      </div>
    )
  }

  const metrics = [
    ...(financialsQuery.data ?? []),
    {
      key: 'awaiting_approval' as const,
      label: 'Pending approvals',
      value: approvalsQuery.data?.total ?? 0,
      description: 'Backend-reported pending approvals',
    },
    {
      key: 'pending_quotations' as const,
      label: 'Quote conversion',
      value: pipelineQuery.data?.conversionRate ?? 0,
      valueFormat: 'percent' as const,
      description: 'Backend-reported quote-to-order conversion',
    },
  ]

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
        {financialsQuery.isError && approvalsQuery.isError && pipelineQuery.isError ? (
          <ErrorState
            title="Command Center unavailable"
            description={presentError(financialsQuery.error, 'page-load').message}
            onRetry={() => {
              void financialsQuery.refetch()
              void approvalsQuery.refetch()
              void pipelineQuery.refetch()
            }}
          />
        ) : (
          <KpiGrid metrics={metrics} />
        )}

        <div className="command-center-g21">
          <div className="command-center-g21-main">
            {pipelineQuery.isPending ? (
              <section className="command-center-card">
                <div className="command-center-card-title">Service pipeline</div>
                <div className="command-center-card-subtitle">Loading...</div>
              </section>
            ) : pipelineQuery.isError ? (
              <section className="command-center-card">
                <EmptyState
                  title="Pipeline unavailable"
                  description={presentError(pipelineQuery.error, 'section-load').message}
                  action={
                    <button
                      type="button"
                      className="command-center-btn command-center-btn-small"
                      onClick={() => void pipelineQuery.refetch()}
                    >
                      Retry
                    </button>
                  }
                />
              </section>
            ) : pipelineQuery.data.stages.length === 0 ? (
              <section className="command-center-card">
                <EmptyState
                  title="No pipeline data"
                  description="The backend returned no pipeline stages."
                />
              </section>
            ) : (
              <LifecycleCard stages={pipelineQuery.data.stages} />
            )}

            {actionItemsQuery.isPending ? (
              <section className="command-center-card">
                <div className="command-center-card-title">My action items</div>
                <div className="command-center-card-subtitle">Loading...</div>
              </section>
            ) : actionItemsQuery.isError ? (
              <section className="command-center-card">
                <EmptyState
                  title="Action items unavailable"
                  description={presentError(actionItemsQuery.error, 'section-load').message}
                  action={
                    <button
                      type="button"
                      className="command-center-btn command-center-btn-small"
                      onClick={() => void actionItemsQuery.refetch()}
                    >
                      Retry
                    </button>
                  }
                />
              </section>
            ) : actionItemsQuery.data.length === 0 ? (
              <section className="command-center-card">
                <EmptyState
                  title="No action items"
                  description="There is currently nothing requiring your attention."
                />
              </section>
            ) : (
              <ActionItemsCard items={actionItemsQuery.data} />
            )}
          </div>

          <div className="command-center-g21-side">
            {approvalsQuery.isPending ? (
              <section className="command-center-card">
                <div className="command-center-card-title">Pending approvals</div>
                <div className="command-center-card-subtitle">Loading...</div>
              </section>
            ) : approvalsQuery.isError ? (
              <section className="command-center-card">
                <EmptyState
                  title="Approvals unavailable"
                  description={presentError(approvalsQuery.error, 'section-load').message}
                  action={
                    <button
                      type="button"
                      className="command-center-btn command-center-btn-small"
                      onClick={() => void approvalsQuery.refetch()}
                    >
                      Retry
                    </button>
                  }
                />
              </section>
            ) : approvalsQuery.data.alerts.length === 0 ? (
              <section className="command-center-card">
                <EmptyState
                  title="No pending approvals"
                  description="The backend returned no approval domains."
                />
              </section>
            ) : (
              <ExecutiveAlertsCard alerts={approvalsQuery.data.alerts} />
            )}

            <section className="command-center-card">
              <div className="command-center-card-header">
                <div>
                  <div className="command-center-card-title">Financial summary</div>
                  <div className="command-center-card-subtitle">
                    Values shown exactly as reported by Command Center.
                  </div>
                </div>
              </div>

              {financialsQuery.isPending ? (
                <div className="command-center-card-subtitle">Loading...</div>
              ) : financialsQuery.isError ? (
                <EmptyState
                  title="Financials unavailable"
                  description={presentError(financialsQuery.error, 'section-load').message}
                  action={
                    <button
                      type="button"
                      className="command-center-btn command-center-btn-small"
                      onClick={() => void financialsQuery.refetch()}
                    >
                      Retry
                    </button>
                  }
                />
              ) : financialsQuery.data.length === 0 ? (
                <EmptyState
                  title="No financial data"
                  description="No financial metrics were returned."
                />
              ) : (
                <div className="space-y-2">
                  {financialsQuery.data.map((metric) => (
                    <div key={metric.label} className="command-center-metric">
                      <label>{metric.label}</label>
                      <strong>{formatMetricValue(metric)}</strong>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        </div>

        {activityQuery.isPending ? (
          <section className="command-center-card">
            <div className="command-center-card-title">Recent system activity</div>
            <div className="command-center-card-subtitle">Loading...</div>
          </section>
        ) : activityQuery.isError ? (
          <section className="command-center-card">
            <EmptyState
              title="Activity unavailable"
              description={presentError(activityQuery.error, 'section-load').message}
              action={
                <button
                  type="button"
                  className="command-center-btn command-center-btn-small"
                  onClick={() => void activityQuery.refetch()}
                >
                  Retry
                </button>
              }
            />
          </section>
        ) : activityQuery.data.length === 0 ? (
          <section className="command-center-card">
            <EmptyState
              title="No recent activity"
              description="No recent Command Center activity was returned."
            />
          </section>
        ) : (
          <RecentActivityCard items={activityQuery.data} />
        )}
      </main>
    </div>
  )
}
