import { IconCircleFilled } from '@tabler/icons-react'
import { cva, type VariantProps } from 'class-variance-authority'
import type { HTMLAttributes } from 'react'

import { cn } from '@/shared/lib/cn'

import { commonStatusDefinitions, type CommonStatus } from './status.config'
import type { StatusDefinition, StatusTone } from './status.types'

const statusBadgeVariants = cva(
  'inline-flex max-w-full items-center gap-1.5 rounded-full border px-2.5 py-1 text-[0.6875rem] font-bold leading-none',
  {
    variants: {
      tone: {
        neutral: 'border-border bg-surface-muted text-foreground-muted',
        info: 'border-brand-200 bg-brand-50 text-brand-700',
        success: 'border-success-200 bg-success-50 text-success-700',
        warning: 'border-warning-200 bg-warning-50 text-warning-700',
        danger: 'border-danger-200 bg-danger-50 text-danger-700',
        purple: 'border-purple-200 bg-purple-50 text-purple-700',
      },
      size: {
        sm: 'px-2 py-0.5 text-[0.625rem]',
        md: 'px-2.5 py-1 text-[0.6875rem]',
      },
    },
    defaultVariants: {
      tone: 'neutral',
      size: 'md',
    },
  },
)

export interface StatusBadgeProps
  extends
    Omit<HTMLAttributes<HTMLSpanElement>, 'children'>,
    Omit<VariantProps<typeof statusBadgeVariants>, 'tone'> {
  status?: CommonStatus
  label?: string
  tone?: StatusTone
  showDot?: boolean
  definitions?: Readonly<Record<string, StatusDefinition>>
}

export function StatusBadge({
  status,
  label,
  tone,
  showDot = true,
  definitions = commonStatusDefinitions,
  size,
  className,
  title,
  ...props
}: StatusBadgeProps) {
  const definition = status ? definitions[status] : undefined
  const resolvedLabel = label ?? definition?.label ?? status ?? 'Unknown'
  const resolvedTone = tone ?? definition?.tone ?? 'neutral'
  const resolvedTitle = title ?? definition?.description

  return (
    <span
      className={cn(statusBadgeVariants({ tone: resolvedTone, size }), className)}
      title={resolvedTitle}
      {...props}
    >
      {showDot ? <IconCircleFilled size={7} className="shrink-0" aria-hidden="true" /> : null}
      <span className="truncate">{resolvedLabel}</span>
    </span>
  )
}
