import { IconArrowDownRight, IconArrowUpRight } from '@tabler/icons-react'
import type { ReactNode } from 'react'

import { cn } from '@/shared/lib/cn'
import { Card } from '@/shared/ui/card'

interface StatCardProps {
  label: string
  value: ReactNode
  description?: string
  trend?: {
    direction: 'up' | 'down'
    label: string
  }
  icon?: ReactNode
}

export function StatCard({ label, value, description, trend, icon }: StatCardProps) {
  const TrendIcon = trend?.direction === 'down' ? IconArrowDownRight : IconArrowUpRight

  return (
    <Card className="p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-foreground-subtle text-[0.5625rem] font-semibold">{label}</p>
          <p className="text-foreground mt-1 text-xl font-extrabold tracking-tight">{value}</p>
        </div>
        {icon ? (
          <span className="bg-brand-50 text-brand-700 grid size-9 place-items-center rounded-xl">
            {icon}
          </span>
        ) : null}
      </div>

      {trend ? (
        <div
          className={cn(
            'mt-3 inline-flex items-center gap-1 text-xs font-bold',
            trend.direction === 'up' ? 'text-success-700' : 'text-danger-700',
          )}
        >
          <TrendIcon size={14} aria-hidden="true" />
          {trend.label}
        </div>
      ) : description ? (
        <p className="text-foreground-subtle mt-3 text-xs">{description}</p>
      ) : null}
    </Card>
  )
}
