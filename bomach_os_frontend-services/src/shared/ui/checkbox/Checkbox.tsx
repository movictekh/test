import { forwardRef, type InputHTMLAttributes } from 'react'

import { cn } from '@/shared/lib/cn'

export type CheckboxProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'>

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      type="checkbox"
      className={cn(
        'border-border text-brand-600 accent-brand-600 focus:ring-brand-300 size-4 rounded focus:ring-2 focus:ring-offset-2',
        className,
      )}
      {...props}
    />
  ),
)

Checkbox.displayName = 'Checkbox'
