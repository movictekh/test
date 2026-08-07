import { IconActivity } from '@tabler/icons-react'
import { Link } from '@tanstack/react-router'

import { Card, CardContent, EmptyState, ProgressBar } from '@/shared/ui'
import { formatCurrency } from '@/shared/lib/formatters'

import type {
  DashboardActivityItem,
  DashboardBranchPerformance,
  DashboardExecutiveAlert,
  DashboardHealthMetric,
  DashboardServicePerformance,
  DashboardSeverity,
} from '../types/dashboard.types'

const alertClasses: Record<DashboardSeverity, string> = {
  danger: 'border-danger-200 bg-danger-50 text-danger-700',
  warning: 'border-warning-200 bg-warning-50 text-warning-700',
  info: 'border-brand-200 bg-brand-50 text-brand-700',
  success: 'border-success-200 bg-success-50 text-success-700',
}

function alertValue(alert: DashboardExecutiveAlert) {
  if (alert.value === undefined) return ''
  if (alert.valueFormat === 'currency') return formatCurrency(alert.value)
  if (alert.valueFormat === 'percent') return `${alert.value}%`
  return alert.value.toLocaleString('en-NG')
}

export function ExecutiveAlerts({ alerts }: { alerts: DashboardExecutiveAlert[] }) {
  return (
    <Card>
      <CardContent className="p-3">
        <h2 className="text-foreground text-[0.6875rem] font-extrabold">Executive alerts</h2>
        <div className="mt-2 space-y-1">
          {alerts.map((alert) => {
            const value = alertValue(alert)
            return (
              <div
                key={alert.id}
                className={`rounded-lg border px-2.5 py-1.75 text-[0.5625rem] leading-[1.3] ${alertClasses[alert.severity]}`}
              >
                <div className="flex flex-wrap items-center gap-1.5">
                  {value ? <strong>{value}</strong> : null}
                  {value ? <span>·</span> : null}
                  {alert.destination ? (
                    <Link
                      to="/app/$section"
                      params={{ section: alert.destination.section }}
                      className="font-semibold hover:underline"
                    >
                      {alert.title}
                    </Link>
                  ) : (
                    <strong>{alert.title}</strong>
                  )}
                </div>
                <p className="mt-0.5 text-[0.53125rem] opacity-85">{alert.description}</p>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}

export function OperationsHealth({ metrics }: { metrics: DashboardHealthMetric[] }) {
  return (
    <Card>
      <CardContent className="p-3">
        <h2 className="text-foreground text-[0.6875rem] font-extrabold">Operations health</h2>
        <div className="mt-2 space-y-1">
          {metrics.map((metric) => (
            <div key={metric.key} className="space-y-0.5">
              <div className="flex items-center justify-between gap-2 text-[0.53125rem]">
                <span className="font-semibold">{metric.label}</span>
                <strong className="text-foreground">{metric.value}%</strong>
              </div>
              <ProgressBar value={metric.value} size="sm" tone={metric.tone} className="h-1.5" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

export function ServicePerformance({ rows }: { rows: DashboardServicePerformance[] }) {
  if (!rows.length)
    return (
      <Card>
        <CardContent>
          <EmptyState
            title="No service performance data"
            description="Verified service performance is not available."
          />
        </CardContent>
      </Card>
    )
  return (
    <Card>
      <CardContent className="p-4">
        <h2 className="text-foreground text-[0.6875rem] font-extrabold">Service Performance</h2>
        <p className="text-foreground-subtle mt-1 text-[0.5625rem]">Based on verified payments.</p>
        <div className="mt-3 space-y-2.5">
          {rows.map((row) => (
            <div key={row.id} className="space-y-1.5">
              <div className="flex items-start justify-between gap-3 text-[0.625rem]">
                <div className="min-w-0">
                  <p className="truncate font-semibold">{row.serviceName}</p>
                  <p className="text-foreground-subtle mt-0.5 text-[0.5625rem]">
                    {row.completionRate}% average completion
                  </p>
                </div>
                <strong className="text-foreground whitespace-nowrap">
                  {formatCurrency(row.verifiedRevenue)}
                </strong>
              </div>
              <ProgressBar
                value={row.completionRate}
                size="sm"
                tone={row.completionRate < 60 ? 'warning' : 'brand'}
              />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

export function BranchPerformance({ rows }: { rows: DashboardBranchPerformance[] }) {
  if (!rows.length)
    return (
      <Card>
        <CardContent>
          <EmptyState
            title="No branch performance data"
            description="Branch performance is not available."
          />
        </CardContent>
      </Card>
    )
  return (
    <Card>
      <CardContent className="p-4">
        <h2 className="text-foreground text-[0.6875rem] font-extrabold">Branch Performance</h2>
        <div className="border-border mt-3 overflow-hidden rounded-xl border">
          <table className="w-full min-w-[560px] border-collapse text-left">
            <thead className="bg-surface-muted text-foreground-subtle text-[0.5625rem] tracking-[0.08em] uppercase">
              <tr>
                <th className="px-3 py-2">Branch</th>
                <th className="px-3 py-2">Requests</th>
                <th className="px-3 py-2">Active orders</th>
                <th className="px-3 py-2">Revenue</th>
                <th className="px-3 py-2">SLA</th>
                <th className="px-3 py-2">CSAT</th>
              </tr>
            </thead>
            <tbody className="divide-border divide-y">
              {rows.map((row) => (
                <tr key={row.id} className="hover:bg-surface-muted text-[0.625rem]">
                  <td className="px-3 py-2.5 font-semibold">{row.branchName}</td>
                  <td className="px-3 py-2.5">{row.requests}</td>
                  <td className="px-3 py-2.5">{row.activeOrders}</td>
                  <td className="px-3 py-2.5 font-semibold">
                    {formatCurrency(row.verifiedRevenue)}
                  </td>
                  <td className="px-3 py-2.5">{row.slaPerformance}%</td>
                  <td className="px-3 py-2.5">{row.clientSatisfaction}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

export function CompactRecentActivity({ items }: { items: DashboardActivityItem[] }) {
  if (!items.length)
    return (
      <Card>
        <CardContent>
          <EmptyState
            title="No recent activity"
            description="Recent service events will appear here."
          />
        </CardContent>
      </Card>
    )
  return (
    <Card>
      <CardContent className="p-4">
        <h2 className="text-foreground text-xs font-extrabold">Recent service activity</h2>
        <div className="divide-border mt-3 divide-y">
          {items.slice(0, 5).map((item) => (
            <div key={item.id} className="flex gap-2.5 py-2">
              <span className="bg-brand-50 text-brand-700 grid size-7 shrink-0 place-items-center rounded-lg">
                <IconActivity size={14} />
              </span>
              <div className="min-w-0">
                <p className="truncate text-[0.625rem] font-semibold">{item.title}</p>
                <p className="text-foreground-subtle text-[0.5625rem]">
                  {item.actor ?? 'System'} · {new Date(item.occurredAt).toLocaleString('en-NG')}
                </p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
