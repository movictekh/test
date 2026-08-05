import { Skeleton } from './Skeleton'

interface PageSkeletonProps {
  sections?: number
  showActions?: boolean
}

export function PageSkeleton({ sections = 2, showActions = true }: PageSkeletonProps) {
  return (
    <div role="status" aria-busy="true" className="min-h-full">
      <span className="sr-only">Loading page</span>

      <div className="border-border bg-surface border-b px-4 py-5 sm:px-5 lg:px-7">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="space-y-3">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-8 w-64 max-w-full" />
            <Skeleton className="h-4 w-[28rem] max-w-full" />
          </div>

          {showActions ? (
            <div className="flex gap-2">
              <Skeleton className="h-10 w-28" />
              <Skeleton className="h-10 w-32" />
            </div>
          ) : null}
        </div>
      </div>

      <div className="space-y-5 p-4 sm:p-5 lg:p-7">
        {Array.from({ length: sections }, (_, index) => (
          <section
            key={index}
            className="border-border bg-surface rounded-card shadow-card border p-5"
          >
            <Skeleton className="h-5 w-40" />
            <Skeleton className="mt-2 h-3 w-72 max-w-full" />
            <div className="mt-5 space-y-3">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-4/5" />
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}
