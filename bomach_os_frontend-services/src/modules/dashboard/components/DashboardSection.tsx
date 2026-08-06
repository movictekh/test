import type { PropsWithChildren, ReactNode } from 'react'

interface DashboardSectionProps extends PropsWithChildren {
  title: string
  description?: string
  action?: ReactNode
}

export function DashboardSection({ title, description, action, children }: DashboardSectionProps) {
  return (
    <section>
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-foreground text-sm font-extrabold">{title}</h2>
          {description ? (
            <p className="text-foreground-subtle mt-1 text-xs">{description}</p>
          ) : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}
