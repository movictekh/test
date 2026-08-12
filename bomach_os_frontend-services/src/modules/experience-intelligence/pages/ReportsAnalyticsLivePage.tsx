import { IconDownload, IconRefresh } from '@tabler/icons-react'
import { useQuery } from '@tanstack/react-query'

import { presentError } from '@/shared/errors'
import { formatCurrency } from '@/shared/lib/formatters'
import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'
import { EmptyState } from '@/shared/ui/empty-state'
import {
  CompactActionButton,
  CompactPageToolbar,
  ModulePageFrame,
  ModulePageStatus,
} from '@/shared/ui/module-controls'

import { reportsApi } from '../reports/reports.api'
import { reportsQueries } from '../reports/reports.queries'
import '../styles/experience-intelligence.css'

function percentage(value: number) {
  return `${value.toFixed(1)}%`
}

function downloadCsv(content: string) {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')

  anchor.href = url
  anchor.download = 'service-performance.csv'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export function ReportsAnalyticsLivePage() {
  const toast = useToast()

  const kpisQuery = useQuery(reportsQueries.kpis())
  const serviceQuery = useQuery(reportsQueries.servicePerformance())
  const branchQuery = useQuery(reportsQueries.branchPerformance())

  const refresh = async () => {
    await Promise.all([kpisQuery.refetch(), serviceQuery.refetch(), branchQuery.refetch()])

    toast.success('Reports & Analytics refreshed')
  }

  const exportServicePerformance = async () => {
    try {
      const csv = await reportsApi.servicePerformanceCsv()
      downloadCsv(csv)
      toast.success('Service Performance exported')
    } catch (error) {
      toast.error('Service Performance export failed', {
        description: presentError(error, 'background-action').message,
      })
    }
  }

  if (kpisQuery.isPending && serviceQuery.isPending && branchQuery.isPending) {
    return (
      <ModulePageStatus title="Reports & Analytics" breadcrumb="Intelligence / Performance">
        <DashboardSkeleton />
      </ModulePageStatus>
    )
  }

  if (kpisQuery.isError) {
    const error = presentError(kpisQuery.error, 'page-load')

    return (
      <ModulePageStatus title="Reports & Analytics" breadcrumb="Intelligence / Performance">
        <ErrorState
          title={error.title}
          description={error.message}
          onRetry={() => void kpisQuery.refetch()}
        />
      </ModulePageStatus>
    )
  }

  if (!kpisQuery.data) {
    return (
      <ModulePageStatus title="Reports & Analytics" breadcrumb="Intelligence / Performance">
        <ErrorState
          title="Reports unavailable"
          description="Business performance KPIs could not be loaded."
          onRetry={() => void kpisQuery.refetch()}
        />
      </ModulePageStatus>
    )
  }

  const kpis = kpisQuery.data

  return (
    <ModulePageFrame
      header={
        <CompactPageToolbar
          title="Reports & Analytics"
          breadcrumb="Intelligence / Performance"
          secondaryAction={
            <CompactActionButton
              disabled={kpisQuery.isFetching || serviceQuery.isFetching || branchQuery.isFetching}
              onClick={() => void refresh()}
            >
              <IconRefresh size={14} />
              Refresh
            </CompactActionButton>
          }
        />
      }
    >
      <main className="experience-content">
        <section className="experience-kpi-grid" aria-label="Business performance summary">
          <article className="experience-kpi-card">
            <div>Quote-to-order conversion</div>
            <strong>{percentage(kpis.quoteToOrderConversion)}</strong>
          </article>

          <article className="experience-kpi-card">
            <div>Average response time</div>
            <strong>{kpis.averageResponseTimeMinutes.toFixed(1)}m</strong>
          </article>

          <article className="experience-kpi-card">
            <div>Gross service margin</div>
            <strong>{percentage(kpis.grossServiceMargin)}</strong>
          </article>

          <article className="experience-kpi-card">
            <div>On-time delivery</div>
            <strong>{percentage(kpis.onTimeDelivery)}</strong>
          </article>
        </section>

        <div className="experience-grid-2">
          <section className="experience-card">
            <header className="experience-card-header">
              <div>
                <div className="experience-card-title">Service Performance</div>
                <div className="experience-card-subtitle">
                  Completed-Order rate and collected invoice revenue by Service
                </div>
              </div>

              <CompactActionButton
                disabled={serviceQuery.isPending || serviceQuery.isError}
                onClick={() => void exportServicePerformance()}
              >
                <IconDownload size={13} />
                Export CSV
              </CompactActionButton>
            </header>

            {serviceQuery.isPending ? (
              <DashboardSkeleton />
            ) : serviceQuery.isError ? (
              <ErrorState
                title="Service Performance unavailable"
                description={presentError(serviceQuery.error, 'section-load').message}
                onRetry={() => void serviceQuery.refetch()}
              />
            ) : serviceQuery.data.length ? (
              serviceQuery.data.map((item) => (
                <div className="experience-metric" key={item.serviceName}>
                  <label>
                    <b>{item.serviceName}</b>
                    <span>{percentage(item.completionRate)} completion rate</span>
                  </label>

                  <div className="experience-progress">
                    <i
                      style={{
                        width: `${Math.max(0, Math.min(100, item.completionRate))}%`,
                      }}
                    />
                  </div>

                  <strong>{formatCurrency(item.revenue)}</strong>
                </div>
              ))
            ) : (
              <EmptyState
                title="No Service performance data"
                description="Service performance will appear when Orders and paid invoices are available."
              />
            )}
          </section>

          <section className="experience-card">
            <header className="experience-card-header">
              <div>
                <div className="experience-card-title">Branch Performance</div>
                <div className="experience-card-subtitle">
                  Requests, active Orders, collected revenue, on-time SLA and CSAT score
                </div>
              </div>
            </header>

            {branchQuery.isPending ? (
              <DashboardSkeleton />
            ) : branchQuery.isError ? (
              <ErrorState
                title="Branch Performance unavailable"
                description={presentError(branchQuery.error, 'section-load').message}
                onRetry={() => void branchQuery.refetch()}
              />
            ) : branchQuery.data.length ? (
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
                    {branchQuery.data.map((item) => (
                      <tr key={item.branchName}>
                        <td>
                          <b>{item.branchName}</b>
                        </td>
                        <td>{item.requests}</td>
                        <td>{item.activeOrders}</td>
                        <td>{formatCurrency(item.revenue)}</td>
                        <td>{percentage(item.sla)}</td>
                        <td>{percentage(item.csat)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                title="No Branch performance data"
                description="Branch performance will appear when Service Requests are linked to Branches."
              />
            )}
          </section>
        </div>
      </main>
    </ModulePageFrame>
  )
}
