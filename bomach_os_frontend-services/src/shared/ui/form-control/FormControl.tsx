import type { ReactNode } from 'react'

import { cn } from '@/shared/lib/cn'

interface FormControlProps {
  id: string
  label: string
  children: ReactNode
  description?: string
  error?: string | undefined
  required?: boolean
  className?: string
}

export function FormControl({
  id,
  label,
  children,
  description,
  error,
  required = false,
  className,
}: FormControlProps) {
  return (
    <div className={cn('space-y-1.5', className)}>
      <label htmlFor={id} className="text-foreground-muted block text-xs font-semibold">
        {label}
        {required ? (
          <span className="text-danger-600 ml-1" aria-hidden="true">
            *
          </span>
        ) : null}
      </label>

      {children}

      {error ? (
        <p id={`${id}-error`} className="text-danger-700 text-xs">
          {error}
        </p>
      ) : description ? (
        <p id={`${id}-description`} className="text-foreground-subtle text-xs">
          {description}
        </p>
      ) : null}
    </div>
  )
}
