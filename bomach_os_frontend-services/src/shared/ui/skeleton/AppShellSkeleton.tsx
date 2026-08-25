import { DashboardSkeleton } from './DashboardSkeleton'
import { Skeleton } from './Skeleton'

export function AppShellSkeleton() {
  return (
    <div role="status" aria-busy="true" className="bg-background min-h-screen">
      <span className="sr-only">Loading application</span>

      <aside className="border-border bg-surface fixed top-0 bottom-0 left-0 hidden w-64 border-r p-3 lg:block">
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

      <div className="min-h-screen lg:pl-64">
        <DashboardSkeleton />
      </div>
    </div>
  )
}
