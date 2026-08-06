import { IconFilePlus, IconPlus, IconUserScreen } from '@tabler/icons-react'
import { Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'

import { useAuth } from '@/app/auth'
import { presentError } from '@/shared/errors'
import { Card, CardContent, DashboardSkeleton, ErrorState, ProgressBar } from '@/shared/ui'

import { dashboardQueries } from '../api/dashboard.queries'
import { AttentionQueue } from '../components/AttentionQueue'
import { DashboardMetricGrid } from '../components/DashboardMetricGrid'
import { OperationalPipeline } from '../components/OperationalPipeline'

const currencyFormatter = new Intl.NumberFormat('en-NG', {
  style: 'currency',
  currency: 'NGN',
  maximumFractionDigits: 0,
})

const servicePerformanceRows = [
  ['Estate Plot Sales', 68, 4_500_000],
  ['Building Construction', 54, 245_000_000],
  ['Cadastral Land Survey', 78, 3_200_000],
  ['Software Development', 24, 12_000_000],
  ['Structural Inspection', 0, 591_250],
] as const

const branchPerformanceRows = [
  ['Enugu', 42, 15, 184_000_000, 93, 94],
  ['Port Harcourt', 21, 7, 62_000_000, 86, 88],
  ['Lagos', 31, 11, 138_000_000, 89, 91],
  ['Abuja', 18, 6, 74_000_000, 91, 93],
] as const

const operationsHealthRows = [
  ['Request response', 88],
  ['Quote turnaround', 82],
  ['Payment verification', 96],
  ['On-time milestones', 87],
  ['Client updates', 79],
] as const

function formatMoney(amount: number) {
  return currencyFormatter.format(amount)
}

export function OperationsDashboardPage() {
  const { user } = useAuth()
  const userId = user?.id ?? ''

  const summaryQuery = useQuery({
    ...dashboardQueries.summary(userId),
    enabled: Boolean(userId),
  })

  if (summaryQuery.isPending) return <DashboardSkeleton />

  if (summaryQuery.isError) {
    const presentation = presentError(summaryQuery.error, 'page-load')
    return (
      <ErrorState
        title={presentation.title}
        description={presentation.message}
        onRetry={() => void summaryQuery.refetch()}
      />
    )
  }

  const summary = summaryQuery.data
  const overviewMetrics =
    summary.configuration && summary.metrics.length < 5
      ? [
          ...summary.metrics,
          {
            key: 'service_configuration' as const,
            label: 'Service Configuration',
            value: summary.configuration.activeServices,
            description: `${summary.configuration.draftServices} drafts · ${summary.configuration.missingWorkflow} missing workflow`,
          },
        ]
      : summary.metrics

  const urgentRequests = summary.attentionItems.filter((item) => item.severity === 'danger').length
  const waitingApprovals = summary.attentionItems.filter(
    (item) => item.severity === 'warning',
  ).length
  const outstandingInvoices =
    summary.metrics.find((metric) => metric.key === 'outstanding_invoices')?.value ?? 0
  const serviceRisk = summary.risks.find((item) => item.severity === 'danger')?.count ?? 0
  const clientSatisfaction = 92

  return (
    <>
      <section className="border-border bg-surface flex flex-col gap-3 border-b px-4 py-2.5 sm:flex-row sm:items-center sm:justify-between lg:px-7">
        <div className="min-w-0">
          <p className="text-brand-600 text-[0.5625rem] font-bold tracking-[0.14em] uppercase">
            Service Command Center
          </p>
          <h1 className="text-foreground truncate text-sm font-extrabold tracking-tight">
            Command Center
          </h1>
          <p className="text-foreground-subtle mt-0.5 truncate text-[0.6875rem]">
            Services / Executive overview
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:justify-end">
          <Link
            to="/portal/dashboard"
            className="border-border bg-surface text-foreground hover:bg-surface-muted rounded-control inline-flex h-8 items-center gap-2 border px-3 text-xs font-semibold transition-colors"
          >
            <IconUserScreen size={15} aria-hidden="true" />
            Client Portal
          </Link>

          <Link
            to="/app/shell/$section"
            params={{ section: 'service-requests' }}
            className="border-border bg-surface text-foreground hover:bg-surface-muted rounded-control inline-flex h-8 items-center gap-2 border px-3 text-xs font-semibold transition-colors"
          >
            <IconFilePlus size={15} aria-hidden="true" />
            New Request
          </Link>

          <Link
            to="/app/shell/$section"
            params={{ section: 'service-catalogue' }}
            className="bg-brand-600 hover:bg-brand-800 rounded-control inline-flex h-8 items-center gap-2 px-3 text-xs font-semibold text-white transition-colors"
          >
            <IconPlus size={15} aria-hidden="true" />
            Create Service
          </Link>
        </div>
      </section>

      <main className="space-y-4 p-4 sm:p-5 lg:p-6">
        <DashboardMetricGrid metrics={overviewMetrics} />

        <div className="grid gap-3 xl:grid-cols-[minmax(0,1.9fr)_minmax(320px,1fr)]">
          <div className="space-y-3">
            <OperationalPipeline
              stages={summary.pipeline}
              title="End-to-end service lifecycle"
              description="Commercial and operational handoff."
            />

            <AttentionQueue
              items={summary.attentionItems}
              title="Requests requiring action"
              description="Prioritized by SLA, value and urgency."
            />
          </div>

          <div className="space-y-3">
            <Card>
              <CardContent className="p-4">
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-foreground text-xs font-extrabold">Executive alerts</h2>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="border-danger-200 bg-danger-50 text-danger-700 rounded-xl border p-3 text-xs leading-5">
                    <b>{urgentRequests || serviceRisk} unreviewed request(s)</b>
                    <br />
                    Assign an owner and contact the client.
                  </div>
                  <div className="border-warning-200 bg-warning-50 text-warning-700 rounded-xl border p-3 text-xs leading-5">
                    <b>{waitingApprovals} approvals waiting</b>
                    <br />
                    Old items may delay revenue and delivery.
                  </div>
                  <div className="border-brand-200 bg-brand-50 text-brand-700 rounded-xl border p-3 text-xs leading-5">
                    <b>{formatMoney(outstandingInvoices)} outstanding</b>
                    <br />
                    Finance follow-up is required.
                  </div>
                  <div className="border-success-200 bg-success-50 text-success-700 rounded-xl border p-3 text-xs leading-5">
                    <b>Client satisfaction is {clientSatisfaction}%</b>
                    <br />
                    Delivery quality remains strong.
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-foreground text-xs font-extrabold">Operations health</h2>
                  </div>
                </div>

                <div className="space-y-3">
                  {operationsHealthRows.map(([label, value]) => (
                    <div key={label} className="space-y-1.5">
                      <div className="flex items-center justify-between gap-3 text-xs">
                        <span className="font-medium">{label}</span>
                        <span className="text-foreground font-bold">{value}%</span>
                      </div>
                      <ProgressBar
                        value={value}
                        size="sm"
                        tone={value < 80 ? 'danger' : value < 90 ? 'warning' : 'success'}
                      />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        <div className="grid gap-3 xl:grid-cols-2">
          <Card>
            <CardContent className="p-4">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-foreground text-xs font-extrabold">Service Performance</h2>
                  <p className="text-foreground-subtle mt-1 text-[0.5625rem]">
                    Based on verified payments.
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                {servicePerformanceRows.map(([label, completion, amount]) => (
                  <div key={label} className="space-y-1.5">
                    <div className="flex items-start justify-between gap-3 text-xs">
                      <div>
                        <p className="font-semibold">{label}</p>
                        <p className="text-foreground-subtle mt-0.5 text-[0.6875rem]">
                          {completion}% average completion
                        </p>
                      </div>
                      <span className="text-foreground font-bold">{formatMoney(amount)}</span>
                    </div>
                    <ProgressBar
                      value={completion}
                      size="sm"
                      tone={completion < 60 ? 'warning' : 'brand'}
                    />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-foreground text-xs font-extrabold">Branch Performance</h2>
                </div>
              </div>

              <div className="border-border overflow-hidden rounded-xl border">
                <div className="bg-surface-muted text-foreground-subtle grid grid-cols-[1.3fr_.8fr_.9fr_1fr_.7fr_.7fr] gap-2 px-3 py-2 text-[0.65rem] font-bold tracking-[0.08em] uppercase">
                  <span>Branch</span>
                  <span>Requests</span>
                  <span>Active Orders</span>
                  <span>Revenue</span>
                  <span>SLA</span>
                  <span>CSAT</span>
                </div>
                <div className="divide-border divide-y">
                  {branchPerformanceRows.map(
                    ([branch, requests, activeOrders, revenue, sla, csat]) => (
                      <div
                        key={branch}
                        className="grid grid-cols-[1.3fr_.8fr_.9fr_1fr_.7fr_.7fr] gap-2 px-3 py-2.5 text-xs"
                      >
                        <span className="font-semibold">{branch}</span>
                        <span>{requests}</span>
                        <span>{activeOrders}</span>
                        <span>{formatMoney(revenue)}</span>
                        <span>{sla}%</span>
                        <span>{csat}%</span>
                      </div>
                    ),
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </>
  )
}
