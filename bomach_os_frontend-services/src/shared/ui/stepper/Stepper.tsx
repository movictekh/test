import { IconCheck } from '@tabler/icons-react'
import type { ReactNode } from 'react'

import { cn } from '@/shared/lib/cn'

export type StepStatus = 'complete' | 'current' | 'upcoming' | 'error'

export interface StepperStep {
  id: string
  label: ReactNode
  description?: ReactNode
  status: StepStatus
}

export interface StepperProps {
  steps: readonly StepperStep[]
  orientation?: 'horizontal' | 'vertical'
  className?: string
}

const circleClasses: Record<StepStatus, string> = {
  complete: 'border-success-600 bg-success-600 text-white',
  current: 'border-brand-600 bg-brand-50 text-brand-700',
  upcoming: 'border-border bg-surface text-foreground-subtle',
  error: 'border-danger-600 bg-danger-50 text-danger-700',
}

export function Stepper({ steps, orientation = 'horizontal', className }: StepperProps) {
  if (orientation === 'vertical') {
    return (
      <ol className={cn('space-y-0', className)}>
        {steps.map((step, index) => (
          <li key={step.id} className="relative flex gap-3 pb-6 last:pb-0">
            {index < steps.length - 1 ? (
              <span className="bg-border absolute top-8 bottom-0 left-[0.9375rem] w-px" />
            ) : null}
            <span
              className={cn(
                'relative z-10 grid size-8 shrink-0 place-items-center rounded-full border-2 text-xs font-black',
                circleClasses[step.status],
              )}
            >
              {step.status === 'complete' ? <IconCheck size={15} /> : index + 1}
            </span>
            <div className="pt-1">
              <p className="text-foreground text-sm font-bold">{step.label}</p>
              {step.description ? (
                <p className="text-foreground-muted mt-1 text-xs leading-5">{step.description}</p>
              ) : null}
            </div>
          </li>
        ))}
      </ol>
    )
  }

  return (
    <ol
      className={cn('grid overflow-x-auto', className)}
      style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(8rem, 1fr))` }}
    >
      {steps.map((step, index) => (
        <li key={step.id} className="relative min-w-32 text-center">
          {index > 0 ? <span className="bg-border absolute top-4 right-1/2 left-0 h-px" /> : null}
          {index < steps.length - 1 ? (
            <span className="bg-border absolute top-4 right-0 left-1/2 h-px" />
          ) : null}
          <span
            className={cn(
              'relative z-10 mx-auto grid size-8 place-items-center rounded-full border-2 text-xs font-black',
              circleClasses[step.status],
            )}
          >
            {step.status === 'complete' ? <IconCheck size={15} /> : index + 1}
          </span>
          <p className="text-foreground mt-2 text-xs font-bold">{step.label}</p>
          {step.description ? (
            <p className="text-foreground-subtle mt-1 text-[0.6875rem] leading-4">
              {step.description}
            </p>
          ) : null}
        </li>
      ))}
    </ol>
  )
}
