import { DashboardSkeleton } from './DashboardSkeleton'
import { Skeleton } from './Skeleton'

const headerSkeletonProps = {
  baseColor: 'rgba(255, 255, 255, 0.2)',
  highlightColor: 'rgba(255, 255, 255, 0.3)',
}

export function AppShellSkeleton() {
  return (
    <div role="status" aria-busy="true" className="bg-background min-h-screen">
      <span className="sr-only">Loading application</span>

      <header className="bg-brand-600 fixed inset-x-0 top-0 z-40 flex h-16 items-center justify-between px-4 lg:px-5">
        <div className="flex items-center gap-3">
          <Skeleton className="size-10 rounded-xl" {...headerSkeletonProps} />
          <div className="space-y-2">
            <Skeleton className="h-3 w-28" {...headerSkeletonProps} />
            <Skeleton className="h-2.5 w-36" {...headerSkeletonProps} />
          </div>
        </div>
        <Skeleton className="hidden h-9 w-80 rounded-full md:block" {...headerSkeletonProps} />
        <Skeleton className="size-9 rounded-full" {...headerSkeletonProps} />
      </header>

      <aside className="border-border bg-surface fixed top-16 bottom-0 left-0 hidden w-64 border-r p-3 lg:block">
        <div className="space-y-5">
          {Array.from({ length: 4 }, (_, sectionIndex) => (
            <div key={sectionIndex} className="space-y-2">
              <Skeleton className="h-2.5 w-24" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ))}
        </div>
      </aside>

      <div className="min-h-screen pt-16 lg:pl-64">
        <DashboardSkeleton />
      </div>
    </div>
  )
}
