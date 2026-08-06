import type { ReactNode } from 'react'
import { useNavigate } from '@tanstack/react-router'

import { Badge, Card, CardContent, EmptyState } from '@/shared/ui'

import type { DashboardAttentionItem } from '../types/dashboard.types'

interface AttentionQueueProps {
  items: DashboardAttentionItem[]
  title?: string
  description?: string
  action?: ReactNode
}

export function AttentionQueue({ items, title, description, action }: AttentionQueueProps) {
  const navigate = useNavigate()
  const heading = title ?? 'Requests requiring action'
  const subheading = description ?? 'Prioritized by SLA, value and urgency.'

  if (items.length === 0) {
    return (
      <Card>
        <CardContent className="p-3.5">
          <div className="mb-2.5 flex items-start justify-between gap-3">
            <div>
              <h2 className="text-foreground text-xs font-extrabold">{heading}</h2>
              <p className="text-foreground-subtle mt-1 text-[0.5625rem]">{subheading}</p>
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
      <CardContent className="p-3.5">
        <div className="mb-2.5 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-foreground text-xs font-extrabold">{heading}</h2>
            <p className="text-foreground-subtle mt-1 text-[0.5625rem]">{subheading}</p>
          </div>
          {action}
        </div>

        <div className="border-border overflow-auto rounded-xl border">
          <table className="w-full min-w-[760px] border-collapse">
            <thead>
              <tr className="bg-surface">
                <th className="text-foreground-subtle border-border px-3 py-2 text-left text-[0.5rem] font-bold tracking-[0.16em] uppercase">
                  Request
                </th>
                <th className="text-foreground-subtle border-border px-3 py-2 text-left text-[0.5rem] font-bold tracking-[0.16em] uppercase">
                  Client
                </th>
                <th className="text-foreground-subtle border-border px-3 py-2 text-left text-[0.5rem] font-bold tracking-[0.16em] uppercase">
                  Service
                </th>
                <th className="text-foreground-subtle border-border px-3 py-2 text-left text-[0.5rem] font-bold tracking-[0.16em] uppercase">
                  Status
                </th>
                <th className="text-foreground-subtle border-border px-3 py-2 text-left text-[0.5rem] font-bold tracking-[0.16em] uppercase">
                  Owner
                </th>
                <th className="text-foreground-subtle border-border px-3 py-2 text-left text-[0.5rem] font-bold tracking-[0.16em] uppercase">
                  Next action
                </th>
              </tr>
            </thead>
            <tbody>
              {items.slice(0, 5).map((item) => {
                const tone =
                  item.statusTone ??
                  (item.severity === 'danger'
                    ? 'danger'
                    : item.severity === 'warning'
                      ? 'warning'
                      : 'info')
                const isInteractive = Boolean(item.destination)

                return (
                  <tr
                    key={item.id}
                    className={[
                      'border-border border-t',
                      isInteractive ? 'hover:bg-surface-muted/40 cursor-pointer' : '',
                    ]
                      .filter(Boolean)
                      .join(' ')}
                    onClick={() => {
                      if (!item.destination) return
                      void navigate({
                        to: '/app/$section',
                        params: { section: item.destination.section },
                      })
                    }}
                    onKeyDown={(event) => {
                      if (!item.destination) return
                      if (event.key !== 'Enter' && event.key !== ' ') return
                      event.preventDefault()
                      void navigate({
                        to: '/app/$section',
                        params: { section: item.destination.section },
                      })
                    }}
                    role={isInteractive ? 'button' : undefined}
                    tabIndex={isInteractive ? 0 : undefined}
                  >
                    <td className="px-3 py-2 align-top">
                      <div className="text-[0.6875rem] font-bold">
                        {item.requestNumber ?? item.recordNumber ?? item.id}
                      </div>
                      <div className="text-foreground-subtle mt-0.5 text-[0.5625rem]">
                        {item.createdLabel ?? item.dueLabel ?? '—'}
                      </div>
                    </td>
                    <td className="px-3 py-2 align-top text-[0.625rem]">{item.client ?? '—'}</td>
                    <td className="px-3 py-2 align-top text-[0.625rem]">{item.service ?? '—'}</td>
                    <td className="px-3 py-2 align-top">
                      <Badge tone={tone} className="px-2 py-0.5 text-[0.5625rem]">
                        {item.statusLabel ?? item.severity}
                      </Badge>
                    </td>
                    <td className="px-3 py-2 align-top text-[0.625rem]">{item.owner ?? '—'}</td>
                    <td className="px-3 py-2 align-top text-[0.625rem]">
                      {item.nextAction ?? item.description ?? '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
