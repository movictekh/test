import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  description?: string
  eyebrow?: string
  actions?: ReactNode
}

export function PageHeader({ title, description, eyebrow, actions }: PageHeaderProps) {
  return (
    <header className="border-border bg-surface sticky top-0 z-20 flex flex-col gap-4 border-b px-5 py-4 sm:flex-row sm:items-center sm:justify-between lg:px-7">
      <div>
        {eyebrow ? (
          <p className="text-brand-600 text-[0.6875rem] font-bold tracking-[0.12em] uppercase">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="text-foreground text-lg font-extrabold tracking-tight">{title}</h1>
        {description ? <p className="text-foreground-subtle mt-1 text-xs">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  )
}
