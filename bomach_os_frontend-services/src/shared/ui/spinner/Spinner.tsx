import { cn } from '@/shared/lib/cn'

interface SpinnerProps {
  className?: string
  label?: string
}

export function Spinner({ className, label = 'Loading' }: SpinnerProps) {
  return (
    <span role="status" className="inline-flex items-center">
      <span
        aria-hidden="true"
        className={cn(
          'size-4 animate-spin rounded-full border-2 border-current border-r-transparent',
          className,
        )}
      />
      <span className="sr-only">{label}</span>
    </span>
  )
}
