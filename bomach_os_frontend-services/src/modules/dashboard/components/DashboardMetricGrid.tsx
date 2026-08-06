import {
  IconClipboardList,
  IconFileInvoice,
  IconPackage,
  IconShieldCheck,
} from '@tabler/icons-react'

import { StatCard } from '@/shared/ui'

import type { DashboardMetric, DashboardMetricKey } from '../types/dashboard.types'

const metricIcons: Record<DashboardMetricKey, typeof IconClipboardList> = {
  open_requests: IconClipboardList,
  pending_quotations: IconFileInvoice,
  awaiting_approval: IconShieldCheck,
  active_orders: IconPackage,
  outstanding_invoices: IconFileInvoice,
  payment_submissions: IconShieldCheck,
  open_tasks: IconClipboardList,
  service_configuration: IconPackage,
}

export function DashboardMetricGrid({ metrics }: { metrics: DashboardMetric[] }) {
  return (
    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
      {metrics.slice(0, 5).map((metric) => {
        const Icon = metricIcons[metric.key]
        return (
          <StatCard
            key={metric.key}
            label={metric.label}
            value={metric.value.toLocaleString('en-NG')}
            description={metric.description}
            {...(metric.trend ? { trend: metric.trend } : {})}
            icon={<Icon size={20} />}
          />
        )
      })}
    </div>
  )
}
