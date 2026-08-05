import { Skeleton } from './Skeleton'

interface DashboardSkeletonProps {
  cards?: number
}

export function DashboardSkeleton({ cards = 4 }: DashboardSkeletonProps) {
  return (
    <div role="status" aria-busy="true" className="min-h-full">
      <span className="sr-only">Loading dashboard</span>

      <div className="border-border bg-surface border-b px-4 py-5 sm:px-5 lg:px-7">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="mt-3 h-8 w-64 max-w-full" />
        <Skeleton className="mt-3 h-4 w-[32rem] max-w-full" />
      </div>

      <div className="space-y-5 p-4 sm:p-5 lg:p-7">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: cards }, (_, index) => (
            <div
              key={index}
              className="border-border bg-surface rounded-card shadow-card border p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-3">
                  <Skeleton className="h-3 w-24" />
                  <Skeleton className="h-8 w-28" />
                  <Skeleton className="h-3 w-32" />
                </div>
                <Skeleton className="size-10 rounded-xl" />
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
          <Skeleton className="rounded-card h-80 w-full" />
          <Skeleton className="rounded-card h-80 w-full" />
        </div>
      </div>
    </div>
  )
}
