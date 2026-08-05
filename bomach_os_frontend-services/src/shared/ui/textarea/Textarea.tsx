import { forwardRef, type TextareaHTMLAttributes } from 'react'

import { cn } from '@/shared/lib/cn'

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, invalid = false, ...props }, ref) => (
    <textarea
      ref={ref}
      aria-invalid={invalid || undefined}
      className={cn(
        'rounded-control border-border bg-surface text-foreground placeholder:text-foreground-subtle hover:border-brand-300 focus:border-brand-500 disabled:bg-surface-muted min-h-28 w-full resize-y border px-3 py-2.5 text-sm shadow-sm transition-colors focus:outline-none disabled:cursor-not-allowed disabled:opacity-60',
        invalid && 'border-danger-600 focus:border-danger-600',
        className,
      )}
      {...props}
    />
  ),
)

Textarea.displayName = 'Textarea'
