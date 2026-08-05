import { Skeleton } from './Skeleton'

interface FormSkeletonProps {
  fields?: number
  columns?: 1 | 2
}

export function FormSkeleton({ fields = 6, columns = 2 }: FormSkeletonProps) {
  return (
    <div
      role="status"
      aria-busy="true"
      className="border-border bg-surface rounded-card shadow-card border p-5"
    >
      <span className="sr-only">Loading form</span>

      <div className="mb-5 space-y-2">
        <Skeleton className="h-5 w-44" />
        <Skeleton className="h-3 w-80 max-w-full" />
      </div>

      <div className={columns === 2 ? 'grid gap-4 sm:grid-cols-2' : 'grid gap-4'}>
        {Array.from({ length: fields }, (_, index) => (
          <div key={index} className="space-y-2">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-10 w-full" />
          </div>
        ))}
      </div>

      <div className="mt-6 flex justify-end gap-2">
        <Skeleton className="h-10 w-24" />
        <Skeleton className="h-10 w-32" />
      </div>
    </div>
  )
}
