import { forwardRef, type SelectHTMLAttributes } from 'react'

import { cn } from '@/shared/lib/cn'

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, invalid = false, children, ...props }, ref) => (
    <select
      ref={ref}
      aria-invalid={invalid || undefined}
      className={cn(
        'rounded-control border-border bg-surface text-foreground hover:border-brand-300 focus:border-brand-500 disabled:bg-surface-muted h-10 w-full border px-3 text-sm shadow-sm transition-colors focus:outline-none disabled:cursor-not-allowed disabled:opacity-60',
        invalid && 'border-danger-600 focus:border-danger-600',
        className,
      )}
      {...props}
    >
      {children}
    </select>
  ),
)

Select.displayName = 'Select'
