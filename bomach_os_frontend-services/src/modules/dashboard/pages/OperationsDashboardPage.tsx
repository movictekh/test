import { IconFilePlus, IconPlus, IconRefresh, IconUserScreen } from '@tabler/icons-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'

import { useAuth } from '@/app/auth'
import { presentError } from '@/shared/errors'
import {
  Badge,
  Button,
  DashboardSkeleton,
  ErrorState,
  SectionErrorState,
  useToast,
} from '@/shared/ui'

import { dashboardKeys } from '../api/dashboard.keys'
import { dashboardQueries } from '../api/dashboard.queries'
import { AttentionQueue } from '../components/AttentionQueue'
import { DashboardMetricGrid } from '../components/DashboardMetricGrid'
import { OperationalPipeline } from '../components/OperationalPipeline'
import {
  BranchPerformance,
  CompactRecentActivity,
  ExecutiveAlerts,
  OperationsHealth,
  ServicePerformance,
} from '../components/PrototypeDashboardPanels'

export function OperationsDashboardPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const toast = useToast()
  const userId = user?.id ?? ''

  const summaryQuery = useQuery({ ...dashboardQueries.summary(userId), enabled: Boolean(userId) })
  const activityQuery = useQuery(dashboardQueries.recentActivity())

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: dashboardKeys.all })
    toast.info('Dashboard refresh requested', {
      description: 'Available information remains visible while fresh data loads.',
    })
  }

  if (summaryQuery.isPending) return <DashboardSkeleton />
  if (summaryQuery.isError) {
    const error = presentError(summaryQuery.error, 'page-load')
    return (
      <ErrorState
        title={error.title}
        description={error.message}
        onRetry={() => void summaryQuery.refetch()}
      />
    )
  }

  const summary = summaryQuery.data
  const metricValue = (key: string) =>
    summary.metrics.find((metric) => metric.key === key)?.value ?? 0

  const lifecycleStages = [
    {
      key: 'request',
      label: 'Request',
      count: metricValue('open_requests'),
      state: 'done' as const,
      destination: { section: 'service-requests' },
    },
    {
      key: 'assessment',
      label: 'Assessment',
      count: summary.myWork.assignedRequests,
      state: 'done' as const,
      destination: { section: 'service-requests' },
    },
    {
      key: 'quotation',
      label: 'Quotation',
      count: metricValue('pending_quotations'),
      state: 'done' as const,
      destination: { section: 'quotations-proposals' },
    },
    {
      key: 'approval',
      label: 'Approval',
      count: metricValue('awaiting_approval'),
      state: 'active' as const,
      destination: { section: 'approval-queue' },
    },
    {
      key: 'invoice-payment',
      label: 'Invoice & Payment',
      count: metricValue('payment_submissions'),
      state: 'pending' as const,
      destination: { section: 'invoices-payments' },
    },
    {
      key: 'service-order',
      label: 'Service Order',
      count: metricValue('active_orders'),
      state: 'pending' as const,
      destination: { section: 'service-orders' },
    },
    {
      key: 'fulfilment',
      label: 'Fulfilment',
      count: summary.myWork.openTasks,
      state: 'pending' as const,
      destination: { section: 'service-orders' },
    },
    {
      key: 'acceptance',
      label: 'Acceptance',
      count: summary.myWork.pendingReviews,
      state: 'pending' as const,
      destination: { section: 'deliverables' },
    },
  ]

  return (
    <>
      <section className="border-border bg-surface flex min-h-12 flex-col gap-2 border-b px-3 py-2 sm:flex-row sm:items-center sm:justify-between lg:px-5">
        <div>
          <h1 className="text-foreground text-[0.8125rem] font-extrabold">
            Service Command Center
          </h1>
          <p className="text-foreground-subtle mt-0.5 text-[0.5625rem]">
            Services / Executive overview
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-[0.625rem]"
            onClick={() => void refresh()}
            disabled={summaryQuery.isFetching || activityQuery.isFetching}
          >
            <IconRefresh size={14} className={summaryQuery.isFetching ? 'animate-spin' : ''} />
            Refresh
          </Button>
          <Link
            to="/portal/dashboard"
            className="border-border rounded-control inline-flex h-7 items-center gap-1.5 border px-2.5 text-[0.625rem] font-semibold"
          >
            <IconUserScreen size={14} />
            Client Portal
          </Link>
          <Link
            to="/app/shell/$section"
            params={{ section: 'service-requests' }}
            className="border-border rounded-control inline-flex h-7 items-center gap-1.5 border px-2.5 text-[0.625rem] font-semibold"
          >
            <IconFilePlus size={14} />
            New Request
          </Link>
          <Link
            to="/app/shell/$section"
            params={{ section: 'service-catalogue' }}
            className="bg-brand-600 rounded-control inline-flex h-7 items-center gap-1.5 px-2.5 text-[0.625rem] font-semibold text-white"
          >
            <IconPlus size={14} />
            Create Service
          </Link>
        </div>
      </section>

      <main className="space-y-3 p-3 sm:p-4 lg:p-5">
        <DashboardMetricGrid metrics={summary.metrics.slice(0, 5)} />

        <div className="grid gap-3 xl:grid-cols-[minmax(0,2.15fr)_minmax(240px,0.55fr)]">
          <div className="space-y-3">
            <OperationalPipeline
              stages={lifecycleStages}
              title="End-to-end service lifecycle"
              description="Commercial and operational handoff"
              action={<Badge tone="neutral">Standard journey</Badge>}
            />
            <AttentionQueue
              items={summary.attentionItems}
              title="Requests requiring action"
              description="Prioritized by SLA, value and urgency."
              action={
                <Link
                  to="/app/shell/$section"
                  params={{ section: 'service-requests' }}
                  className="border-border bg-surface text-foreground hover:bg-surface-muted rounded-control inline-flex h-7 items-center border px-2.5 text-[0.625rem] font-semibold"
                >
                  View all
                </Link>
              }
            />
          </div>
          <div className="space-y-3">
            <ExecutiveAlerts alerts={summary.executiveAlerts} />
            <OperationsHealth metrics={summary.operationsHealth} />
          </div>
        </div>

        <div className="grid gap-3 xl:grid-cols-2">
          <ServicePerformance rows={summary.servicePerformance} />
          <BranchPerformance rows={summary.branchPerformance} />
        </div>

        {activityQuery.isPending ? (
          <DashboardSkeleton />
        ) : activityQuery.isError ? (
          <SectionErrorState
            title="Recent service activity could not be loaded"
            description={presentError(activityQuery.error, 'section-load').message}
            onRetry={() => void activityQuery.refetch()}
          />
        ) : (
          <CompactRecentActivity items={activityQuery.data} />
        )}
      </main>
    </>
  )
}
