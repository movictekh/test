import {
  IconAlertTriangle,
  IconCircleCheck,
  IconInfoCircle,
  IconAlertOctagon,
  IconX,
} from '@tabler/icons-react'
import { cva, type VariantProps } from 'class-variance-authority'
import type { HTMLAttributes, ReactNode } from 'react'

import { cn } from '@/shared/lib/cn'
import { Button } from '@/shared/ui/button'

const alertVariants = cva('rounded-card flex gap-3 border p-4', {
  variants: {
    tone: {
      info: 'border-brand-200 bg-brand-50 text-brand-800',
      success: 'border-success-200 bg-success-50 text-success-700',
      warning: 'border-warning-200 bg-warning-50 text-warning-700',
      danger: 'border-danger-200 bg-danger-50 text-danger-700',
      neutral: 'border-border bg-surface-muted text-foreground',
    },
  },
  defaultVariants: {
    tone: 'info',
  },
})

const iconContainerVariants = cva('grid size-9 shrink-0 place-items-center rounded-full', {
  variants: {
    tone: {
      info: 'bg-brand-100 text-brand-700',
      success: 'bg-success-100 text-success-700',
      warning: 'bg-warning-100 text-warning-700',
      danger: 'bg-danger-100 text-danger-700',
      neutral: 'bg-surface-subtle text-foreground-muted',
    },
  },
  defaultVariants: {
    tone: 'info',
  },
})

const defaultIcons = {
  info: IconInfoCircle,
  success: IconCircleCheck,
  warning: IconAlertTriangle,
  danger: IconAlertOctagon,
  neutral: IconInfoCircle,
} as const

export interface AlertProps
  extends Omit<HTMLAttributes<HTMLDivElement>, 'title'>, VariantProps<typeof alertVariants> {
  title: ReactNode
  description?: ReactNode
  icon?: ReactNode
  actions?: ReactNode
  dismissLabel?: string
  onDismiss?: () => void
}

export function Alert({
  title,
  description,
  icon,
  actions,
  tone = 'info',
  dismissLabel = 'Dismiss message',
  onDismiss,
  className,
  ...props
}: AlertProps) {
  const resolvedTone = tone ?? 'info'
  const DefaultIcon = defaultIcons[resolvedTone]
  const role = resolvedTone === 'danger' || resolvedTone === 'warning' ? 'alert' : 'status'

  return (
    <div role={role} className={cn(alertVariants({ tone: resolvedTone }), className)} {...props}>
      <span className={iconContainerVariants({ tone: resolvedTone })}>
        {icon ?? <DefaultIcon size={19} aria-hidden="true" />}
      </span>

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-bold">{title}</p>
            {description ? (
              <div className="mt-1 text-xs leading-5 opacity-85">{description}</div>
            ) : null}
          </div>

          {onDismiss ? (
            <Button
              variant="ghost"
              size="icon"
              className="-mt-2 -mr-2 size-8 shrink-0 text-current hover:bg-black/5 hover:text-current"
              aria-label={dismissLabel}
              onClick={onDismiss}
            >
              <IconX size={16} />
            </Button>
          ) : null}
        </div>

        {actions ? <div className="mt-3 flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
    </div>
  )
}
