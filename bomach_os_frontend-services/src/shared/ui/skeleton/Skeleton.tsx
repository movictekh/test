import type { HTMLAttributes } from 'react'

import { cn } from '@/shared/lib/cn'

export type SkeletonProps = HTMLAttributes<HTMLDivElement>

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={cn('bg-surface-subtle animate-pulse rounded-md', className)}
      {...props}
    />
  )
}
