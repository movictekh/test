import type { HTMLAttributes } from 'react'

import { cn } from '@/shared/lib/cn'

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={cn('bg-surface-subtle animate-pulse rounded-md', className)}
      {...props}
    />
  )
}
