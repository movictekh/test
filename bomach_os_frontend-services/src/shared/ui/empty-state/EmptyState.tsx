import { IconInbox } from '@tabler/icons-react'
import type { ReactNode } from 'react'

interface EmptyStateProps {
  title: string
  description: string
  action?: ReactNode
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="rounded-card border-border bg-surface flex min-h-52 flex-col items-center justify-center border border-dashed px-6 py-10 text-center">
      <span className="bg-brand-50 text-brand-700 grid size-12 place-items-center rounded-full">
        <IconInbox size={24} aria-hidden="true" />
      </span>
      <h2 className="text-foreground mt-4 text-sm font-bold">{title}</h2>
      <p className="text-foreground-subtle mt-1 max-w-md text-xs leading-5">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  )
}
