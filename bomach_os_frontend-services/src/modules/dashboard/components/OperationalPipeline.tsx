import { Link } from '@tanstack/react-router'
import type { ReactNode } from 'react'

import { Card, CardContent } from '@/shared/ui'

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
            <h2 className="text-foreground text-sm font-extrabold">{heading}</h2>
            <p className="text-foreground-subtle mt-1 text-xs">{subheading}</p>
          </div>
          {action}
        </div>

        <div className="space-y-2">
          {stages.map((stage, index) => {
            const content = (
              <div className="hover:bg-surface-muted flex items-center justify-between gap-3 rounded-lg px-2 py-2">
                <div className="flex min-w-0 items-center gap-3">
                  <span className="bg-brand-50 text-brand-700 grid size-7 shrink-0 place-items-center rounded-full text-xs font-extrabold">
                    {index + 1}
                  </span>
                  <span className="truncate text-sm font-semibold">{stage.label}</span>
                </div>
                <span className="text-foreground text-lg font-extrabold">
                  {stage.count.toLocaleString('en-NG')}
                </span>
              </div>
            )

            return stage.destination ? (
              <Link
                key={stage.key}
                to="/app/shell/$section"
                params={{ section: stage.destination.section }}
                className="block"
              >
                {content}
              </Link>
            ) : (
              <div key={stage.key}>{content}</div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
