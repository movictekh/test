import { IconAlertTriangle, IconArrowRight } from '@tabler/icons-react'
import type { ReactNode } from 'react'
import { Link } from '@tanstack/react-router'

import { Badge, Card, CardContent, EmptyState } from '@/shared/ui'

import type { DashboardAttentionItem } from '../types/dashboard.types'

const toneMap = {
  info: 'info',
  warning: 'warning',
  danger: 'danger',
} as const

interface AttentionQueueProps {
  items: DashboardAttentionItem[]
  title?: string
  description?: string
  action?: ReactNode
}

export function AttentionQueue({ items, title, description, action }: AttentionQueueProps) {
  const heading = title ?? 'Requests requiring action'
  const subheading =
    description ?? 'Prioritized by SLA, value and urgency for operational follow-up.'

  if (items.length === 0) {
    return (
      <Card>
        <CardContent className="p-4">
          <div className="mb-3 flex items-start justify-between gap-3">
            <div>
              <h2 className="text-foreground text-sm font-extrabold">{heading}</h2>
              <p className="text-foreground-subtle mt-1 text-xs">{subheading}</p>
            </div>
            {action}
          </div>
          <EmptyState
            title="You are all caught up"
            description="No operational items currently require your attention."
          />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent className="p-4">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-foreground text-sm font-extrabold">{heading}</h2>
            <p className="text-foreground-subtle mt-1 text-xs">{subheading}</p>
          </div>
          {action}
        </div>

        <div className="divide-border border-border divide-y overflow-hidden rounded-xl border">
          {items.slice(0, 6).map((item) => (
            <article key={item.id} className="flex items-start gap-3 p-3">
              <span className="bg-warning-50 text-warning-700 mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg">
                <IconAlertTriangle size={16} aria-hidden="true" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-foreground text-sm font-bold">{item.title}</p>
                  <Badge tone={toneMap[item.severity]}>{item.severity}</Badge>
                </div>
                <p className="text-foreground-subtle mt-1 text-xs leading-5">{item.description}</p>
                <div className="text-foreground-subtle mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[0.6875rem]">
                  {item.recordNumber ? <span>{item.recordNumber}</span> : null}
                  {item.dueLabel ? <span>{item.dueLabel}</span> : null}
                </div>
              </div>
              {item.destination ? (
                <Link
                  to="/app/shell/$section"
                  params={{ section: item.destination.section }}
                  className="text-brand-700 hover:bg-brand-50 inline-flex size-8 shrink-0 items-center justify-center rounded-lg"
                  aria-label={`Open ${item.title}`}
                >
                  <IconArrowRight size={17} />
                </Link>
              ) : null}
            </article>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
