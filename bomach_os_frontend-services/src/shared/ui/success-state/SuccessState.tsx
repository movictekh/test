import { IconCircleCheck } from '@tabler/icons-react'
import type { HTMLAttributes, ReactNode } from 'react'

import { cn } from '@/shared/lib/cn'

export interface SuccessStateProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  title: ReactNode
  description?: ReactNode
  reference?: string
  primaryAction?: ReactNode
  secondaryAction?: ReactNode
  icon?: ReactNode
  compact?: boolean
}

export function SuccessState({
  title,
  description,
  reference,
  primaryAction,
  secondaryAction,
  icon,
  compact = false,
  className,
  ...props
}: SuccessStateProps) {
  return (
    <div
      role="status"
      className={cn(
        'rounded-card border-success-200 bg-success-50 flex flex-col items-center justify-center border px-6 text-center',
        compact ? 'min-h-52 py-8' : 'min-h-80 py-12',
        className,
      )}
      {...props}
    >
      <span className="bg-success-100 text-success-700 grid size-14 place-items-center rounded-full">
        {icon ?? <IconCircleCheck size={29} aria-hidden="true" />}
      </span>

      <h2 className="text-success-700 mt-5 text-lg font-black">{title}</h2>

      {description ? (
        <div className="text-success-700/80 mt-2 max-w-lg text-sm leading-6">{description}</div>
      ) : null}

      {reference ? (
        <p className="border-success-200 bg-surface text-success-700 rounded-control mt-4 border px-3 py-2 font-mono text-xs font-bold">
          {reference}
        </p>
      ) : null}

      {primaryAction || secondaryAction ? (
        <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
          {secondaryAction}
          {primaryAction}
        </div>
      ) : null}
    </div>
  )
}
