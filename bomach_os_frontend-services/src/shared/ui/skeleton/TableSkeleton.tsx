import { Skeleton } from './Skeleton'

interface TableSkeletonProps {
  rows?: number
  columns?: number
  showToolbar?: boolean
}

export function TableSkeleton({ rows = 6, columns = 5, showToolbar = true }: TableSkeletonProps) {
  return (
    <div
      role="status"
      aria-busy="true"
      className="border-border bg-surface rounded-card shadow-card border"
    >
      <span className="sr-only">Loading table</span>

      {showToolbar ? (
        <div className="border-border flex flex-col gap-3 border-b p-4 sm:flex-row sm:items-center sm:justify-between">
          <Skeleton className="h-10 w-full sm:w-72" />
          <div className="flex gap-2">
            <Skeleton className="h-10 w-24" />
            <Skeleton className="h-10 w-28" />
          </div>
        </div>
      ) : null}

      <div className="overflow-hidden">
        <div
          className="border-border bg-surface-muted grid gap-4 border-b px-4 py-3"
          style={{ gridTemplateColumns: `repeat(${columns}, minmax(7rem, 1fr))` }}
        >
          {Array.from({ length: columns }, (_, index) => (
            <Skeleton key={index} className="h-3 w-20" />
          ))}
        </div>

        {Array.from({ length: rows }, (_, rowIndex) => (
          <div
            key={rowIndex}
            className="border-border grid gap-4 border-b px-4 py-4 last:border-b-0"
            style={{ gridTemplateColumns: `repeat(${columns}, minmax(7rem, 1fr))` }}
          >
            {Array.from({ length: columns }, (_, columnIndex) => (
              <Skeleton key={columnIndex} className={columnIndex === 0 ? 'h-4 w-28' : 'h-4 w-20'} />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
