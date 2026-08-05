import { forwardRef, type InputHTMLAttributes } from 'react'

import { cn } from '@/shared/lib/cn'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, invalid = false, ...props }, ref) => (
    <input
      ref={ref}
      aria-invalid={invalid || undefined}
      className={cn(
        'rounded-control border-border bg-surface text-foreground placeholder:text-foreground-subtle hover:border-brand-300 focus:border-brand-500 disabled:bg-surface-muted h-10 w-full border px-3 text-sm shadow-sm transition-colors focus:outline-none disabled:cursor-not-allowed disabled:opacity-60',
        invalid && 'border-danger-600 focus:border-danger-600',
        className,
      )}
      {...props}
    />
  ),
)

Input.displayName = 'Input'
