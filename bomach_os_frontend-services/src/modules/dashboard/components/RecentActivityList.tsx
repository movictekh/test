import { IconActivity } from '@tabler/icons-react'
import { Link } from '@tanstack/react-router'

import { Card, CardContent, EmptyState } from '@/shared/ui'

import type { DashboardActivityItem } from '../types/dashboard.types'

function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat('en-NG', {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(date)
}

export function RecentActivityList({ items }: { items: DashboardActivityItem[] }) {
  if (items.length === 0) {
    return (
      <Card>
        <CardContent>
          <EmptyState
            title="No recent activity"
            description="Operational activity will appear here as work progresses."
          />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent className="divide-border divide-y p-0">
        {items.slice(0, 8).map((item) => {
          const content = (
            <article className="hover:bg-surface-muted flex gap-3 p-4">
              <span className="bg-brand-50 text-brand-700 mt-0.5 grid size-8 shrink-0 place-items-center rounded-full">
                <IconActivity size={16} />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold">{item.title}</p>
                {item.description ? (
                  <p className="text-foreground-subtle mt-1 text-xs leading-5">
                    {item.description}
                  </p>
                ) : null}
                <p className="text-foreground-subtle mt-2 text-[0.6875rem]">
                  {item.actor ? `${item.actor} · ` : ''}
                  {formatDate(item.occurredAt)}
                </p>
              </div>
            </article>
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
