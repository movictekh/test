import { Link } from '@tanstack/react-router'
import type { ReactNode } from 'react'

import { Badge, Card, CardContent } from '@/shared/ui'

import type { DashboardPipelineStage } from '../types/dashboard.types'

interface OperationalPipelineProps {
  stages: DashboardPipelineStage[]
  title?: string
  description?: string
  action?: ReactNode
}

export function OperationalPipeline({
  stages,
  title,
  description,
  action,
}: OperationalPipelineProps) {
  const heading = title ?? 'End-to-end service lifecycle'
  const subheading = description ?? 'Commercial and operational handoff across the service flow.'

  return (
    <Card>
      <CardContent className="p-4">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-foreground text-xs font-extrabold">{heading}</h2>
            <p className="text-foreground-subtle mt-1 text-[0.5625rem]">{subheading}</p>
          </div>
          {action}
        </div>

        <div className="grid auto-cols-[minmax(95px,1fr)] grid-flow-col gap-2 overflow-x-auto pb-1">
          {stages.map((stage, index) => {
            const stateLabel =
              stage.state === 'done'
                ? 'Completed'
                : stage.state === 'active'
                  ? 'In progress'
                  : 'Pending'

            const content = (
              <div className="border-border bg-surface-muted hover:bg-surface flex h-full min-h-[4.75rem] flex-col rounded-xl border p-2.5 transition-colors">
                <span className="text-foreground-subtle text-[0.5625rem] font-bold tracking-[0.12em] uppercase">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <div className="mt-1 min-w-0 flex-1">
                  <p className="text-foreground truncate text-[0.8125rem] font-semibold">
                    {stage.label}
                  </p>
                  <div className="mt-1">
                    <Badge
                      tone={
                        stage.state === 'done'
                          ? 'success'
                          : stage.state === 'active'
                            ? 'info'
                            : 'neutral'
                      }
                      className="px-2 py-0.5 text-[0.5625rem]"
                    >
                      {stateLabel}
                    </Badge>
                  </div>
                </div>
              </div>
            )

            return stage.destination ? (
              <Link
                key={stage.key}
                to="/app/$section"
                params={{ section: stage.destination.section }}
                className="block h-full"
              >
                {content}
              </Link>
            ) : (
              <div key={stage.key} className="h-full">
                {content}
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
