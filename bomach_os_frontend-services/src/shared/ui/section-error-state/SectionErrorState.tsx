import { IconAlertTriangle, IconRefresh } from '@tabler/icons-react'
import type { HTMLAttributes, ReactNode } from 'react'

import { cn } from '@/shared/lib/cn'
import { Button } from '@/shared/ui/button'

export interface SectionErrorStateProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: ReactNode
  description?: ReactNode
  onRetry?: () => void
  retryLabel?: string
  action?: ReactNode
}

export function SectionErrorState({
  title = 'This section could not be loaded',
  description = 'The rest of the page is still available. Try loading this section again.',
  onRetry,
  retryLabel = 'Retry section',
  action,
  className,
  ...props
}: SectionErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        'border-danger-200 bg-danger-50 rounded-card flex min-h-36 items-start gap-3 border p-4',
        className,
      )}
      {...props}
    >
      <span className="bg-danger-100 text-danger-700 grid size-10 shrink-0 place-items-center rounded-full">
        <IconAlertTriangle size={20} aria-hidden="true" />
      </span>

      <div className="min-w-0 flex-1">
        <h3 className="text-danger-700 text-sm font-bold">{title}</h3>
        <div className="text-danger-700/80 mt-1 max-w-xl text-xs leading-5">{description}</div>

        {onRetry || action ? (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {onRetry ? (
              <Button variant="outline" size="sm" onClick={onRetry}>
                <IconRefresh size={15} aria-hidden="true" />
                {retryLabel}
              </Button>
            ) : null}
            {action}
          </div>
        ) : null}
      </div>
    </div>
  )
}
