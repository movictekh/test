import { IconAlertTriangle } from '@tabler/icons-react'

import { Button } from '@/shared/ui/button'

interface ErrorStateProps {
  title?: string
  description?: string
  onRetry?: () => void
}

export function ErrorState({
  title = 'Something went wrong',
  description = 'The information could not be loaded. Please try again.',
  onRetry,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="rounded-card border-danger-200 bg-danger-50 flex min-h-52 flex-col items-center justify-center border px-6 py-10 text-center"
    >
      <span className="bg-danger-100 text-danger-700 grid size-12 place-items-center rounded-full">
        <IconAlertTriangle size={24} aria-hidden="true" />
      </span>
      <h2 className="text-danger-700 mt-4 text-sm font-bold">{title}</h2>
      <p className="text-danger-700/80 mt-1 max-w-md text-xs leading-5">{description}</p>
      {onRetry ? (
        <Button variant="outline" size="sm" className="mt-5" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  )
}
