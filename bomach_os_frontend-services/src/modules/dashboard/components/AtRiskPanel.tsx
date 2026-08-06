import { Link } from '@tanstack/react-router'

import { Badge, Card, CardContent, EmptyState } from '@/shared/ui'

import type { DashboardRiskItem } from '../types/dashboard.types'

export function AtRiskPanel({ items }: { items: DashboardRiskItem[] }) {
  if (items.length === 0) {
    return (
      <Card>
        <CardContent>
          <EmptyState
            title="No work currently at risk"
            description="There are no overdue or near-deadline records in this view."
          />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent className="space-y-3">
        {items.slice(0, 5).map((item) => {
          const content = (
            <div className="border-border hover:bg-surface-muted flex items-start justify-between gap-3 rounded-lg border p-3">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-bold">{item.label}</p>
                  <Badge tone={item.severity}>{item.count}</Badge>
                </div>
                <p className="text-foreground-subtle mt-1 text-xs leading-5">{item.description}</p>
              </div>
            </div>
          )

          return item.destination ? (
            <Link
              key={item.id}
              to="/app/$section"
              params={{ section: item.destination.section }}
              className="block"
            >
              {content}
            </Link>
          ) : (
            <div key={item.id}>{content}</div>
          )
        })}
      </CardContent>
    </Card>
  )
}
