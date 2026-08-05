import type { HTMLAttributes } from 'react'

import { cn } from '@/shared/lib/cn'

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <section
      className={cn('rounded-card border-border bg-surface shadow-card border', className)}
      {...props}
    />
  )
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('border-border flex items-start justify-between gap-4 border-b p-5', className)}
      {...props}
    />
  )
}

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn('text-foreground text-sm font-bold', className)} {...props} />
}

export function CardDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('text-foreground-subtle mt-1 text-xs', className)} {...props} />
}

export function CardContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('p-5', className)} {...props} />
}

export function CardFooter({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('border-border flex items-center justify-end gap-2 border-t p-4', className)}
      {...props}
    />
  )
}
