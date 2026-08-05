import type { HTMLAttributes, ReactNode } from 'react'

import { cn } from '@/shared/lib/cn'

export interface ProgressBarProps extends Omit<HTMLAttributes<HTMLDivElement>, 'children'> {
  value: number
  max?: number
  label?: ReactNode
  showValue?: boolean
  tone?: 'brand' | 'success' | 'warning' | 'danger'
  size?: 'sm' | 'md' | 'lg'
}

const toneClasses = {
  brand: 'bg-brand-600',
  success: 'bg-success-600',
  warning: 'bg-warning-600',
  danger: 'bg-danger-600',
} as const

const sizeClasses = {
  sm: 'h-1.5',
  md: 'h-2.5',
  lg: 'h-4',
} as const

export function ProgressBar({
  value,
  max = 100,
  label,
  showValue = false,
  tone = 'brand',
  size = 'md',
  className,
  ...props
}: ProgressBarProps) {
  const safeMax = max > 0 ? max : 100
  const normalized = Math.min(Math.max(value, 0), safeMax)
  const percentage = Math.round((normalized / safeMax) * 100)

  return (
    <div className={className} {...props}>
      {label || showValue ? (
        <div className="mb-2 flex items-center justify-between gap-3 text-xs">
          {label ? <span className="text-foreground-muted font-semibold">{label}</span> : <span />}
          {showValue ? <span className="text-foreground font-bold">{percentage}%</span> : null}
        </div>
      ) : null}

      <div
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={safeMax}
        aria-valuenow={normalized}
        className={cn('bg-surface-subtle overflow-hidden rounded-full', sizeClasses[size])}
      >
        <div
          className={cn('h-full rounded-full transition-[width] duration-300', toneClasses[tone])}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}
