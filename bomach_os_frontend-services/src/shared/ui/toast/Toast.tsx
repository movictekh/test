import {
  IconAlertTriangle,
  IconCircleCheck,
  IconInfoCircle,
  IconAlertOctagon,
  IconX,
} from '@tabler/icons-react'
import { cva } from 'class-variance-authority'
import { useEffect, useState } from 'react'

import { cn } from '@/shared/lib/cn'
import { Button } from '@/shared/ui/button'

import type { ToastRecord } from './toast.types'

const toastVariants = cva(
  'pointer-events-auto w-full overflow-hidden rounded-card border bg-surface shadow-overlay',
  {
    variants: {
      tone: {
        info: 'border-brand-200',
        success: 'border-success-200',
        warning: 'border-warning-200',
        danger: 'border-danger-200',
      },
    },
  },
)

const iconVariants = cva('grid size-9 shrink-0 place-items-center rounded-full', {
  variants: {
    tone: {
      info: 'bg-brand-100 text-brand-700',
      success: 'bg-success-100 text-success-700',
      warning: 'bg-warning-100 text-warning-700',
      danger: 'bg-danger-100 text-danger-700',
    },
  },
})

const icons = {
  info: IconInfoCircle,
  success: IconCircleCheck,
  warning: IconAlertTriangle,
  danger: IconAlertOctagon,
} as const

interface ToastProps {
  toast: ToastRecord
  onDismiss: (id: string) => void
}

export function Toast({ toast, onDismiss }: ToastProps) {
  const [paused, setPaused] = useState(false)
  const Icon = icons[toast.tone]

  useEffect(() => {
    if (toast.duration <= 0 || paused) {
      return
    }

    const timer = window.setTimeout(() => onDismiss(toast.id), toast.duration)

    return () => window.clearTimeout(timer)
  }, [onDismiss, paused, toast.duration, toast.id])

  const role = toast.tone === 'danger' || toast.tone === 'warning' ? 'alert' : 'status'
  const ariaLive = toast.tone === 'danger' ? 'assertive' : 'polite'

  return (
    <div
      role={role}
      aria-live={ariaLive}
      className={cn(toastVariants({ tone: toast.tone }))}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) {
          setPaused(false)
        }
      }}
    >
      <div className="flex gap-3 p-4">
        <span className={iconVariants({ tone: toast.tone })}>
          <Icon size={19} aria-hidden="true" />
        </span>

        <div className="min-w-0 flex-1">
          <p className="text-foreground text-sm font-bold">{toast.title}</p>
          {toast.description ? (
            <div className="text-foreground-muted mt-1 text-xs leading-5">{toast.description}</div>
          ) : null}

          {toast.action ? (
            <button
              type="button"
              className="text-brand-700 mt-2 text-xs font-bold hover:underline"
              onClick={() => {
                toast.action?.onClick()
                onDismiss(toast.id)
              }}
            >
              {toast.action.label}
            </button>
          ) : null}
        </div>

        <Button
          variant="ghost"
          size="icon"
          className="-mt-2 -mr-2 size-8 shrink-0"
          aria-label="Dismiss notification"
          onClick={() => onDismiss(toast.id)}
        >
          <IconX size={16} />
        </Button>
      </div>

      {toast.duration > 0 ? (
        <div
          className={cn(
            'h-0.5 origin-left',
            toast.tone === 'info' && 'bg-brand-500',
            toast.tone === 'success' && 'bg-success-600',
            toast.tone === 'warning' && 'bg-warning-600',
            toast.tone === 'danger' && 'bg-danger-600',
            !paused && 'animate-[toast-progress_linear_forwards]',
          )}
          style={{ animationDuration: `${toast.duration}ms` }}
          aria-hidden="true"
        />
      ) : null}
    </div>
  )
}
