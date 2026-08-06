import { Card, CardContent } from '@/shared/ui'

import type { DashboardMyWork } from '../types/dashboard.types'

export function MyWorkPanel({ work }: { work: DashboardMyWork }) {
  const items = [
    ['Assigned requests', work.assignedRequests],
    ['Active orders', work.activeOrders],
    ['Open tasks', work.openTasks],
    ['Pending reviews', work.pendingReviews],
  ] as const

  return (
    <Card>
      <CardContent className="grid grid-cols-2 gap-3">
        {items.map(([label, value]) => (
          <div key={label} className="bg-surface-muted rounded-xl p-3">
            <p className="text-foreground-subtle text-xs">{label}</p>
            <p className="text-foreground mt-1 text-xl font-extrabold">
              {value.toLocaleString('en-NG')}
            </p>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
