import { Link } from '@tanstack/react-router'
import type { PropsWithChildren } from 'react'

import { cn } from '@/shared/lib/cn'

import { getRecordDestination } from './record-links'

export function RecordLink({
  entityType,
  entityId,
  children,
  className,
}: PropsWithChildren<{
  entityType: string
  entityId: string
  className?: string
}>) {
  const destination = getRecordDestination(entityType, entityId)

  if (!destination) return <>{children}</>

  return (
    <Link
      to="/app/$section"
      params={{ section: destination.section }}
      search={destination.search}
      className={cn('text-brand-700 font-semibold hover:underline', className)}
      onClick={(event) => event.stopPropagation()}
    >
      {children}
    </Link>
  )
}
