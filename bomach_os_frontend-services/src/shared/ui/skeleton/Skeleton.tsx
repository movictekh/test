import type { ComponentProps } from 'react'
import ReactLoadingSkeleton from 'react-loading-skeleton'
import 'react-loading-skeleton/dist/skeleton.css'

import { cn } from '@/shared/lib/cn'

export type SkeletonProps = ComponentProps<typeof ReactLoadingSkeleton>

export function Skeleton({ className, borderRadius = '0.375rem', ...props }: SkeletonProps) {
  return <ReactLoadingSkeleton className={cn(className)} borderRadius={borderRadius} {...props} />
}
