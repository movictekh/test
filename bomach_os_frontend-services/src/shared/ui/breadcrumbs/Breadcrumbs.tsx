import { IconChevronRight, IconHome } from '@tabler/icons-react'
import { Link } from '@tanstack/react-router'

import { cn } from '@/shared/lib/cn'

export interface BreadcrumbItem {
  label: string
  to?: '/app/dashboard'
}

export interface BreadcrumbsProps {
  items: readonly BreadcrumbItem[]
  className?: string
}

export function Breadcrumbs({ items, className }: BreadcrumbsProps) {
  return (
    <nav aria-label="Breadcrumb" className={className}>
      <ol className="text-foreground-subtle flex flex-wrap items-center gap-1.5 text-xs">
        {items.map((item, index) => {
          const last = index === items.length - 1

          return (
            <li key={index} className="flex min-w-0 items-center gap-1.5">
              {index > 0 ? <IconChevronRight size={13} aria-hidden="true" /> : null}
              {item.to && !last ? (
                <Link
                  to={item.to}
                  className="hover:text-brand-700 inline-flex items-center gap-1 font-semibold"
                >
                  {index === 0 ? <IconHome size={13} aria-hidden="true" /> : null}
                  <span>{item.label}</span>
                </Link>
              ) : (
                <span
                  className={cn(
                    'inline-flex items-center gap-1 truncate',
                    last && 'text-foreground font-semibold',
                  )}
                  aria-current={last ? 'page' : undefined}
                >
                  {index === 0 ? <IconHome size={13} aria-hidden="true" /> : null}
                  {item.label}
                </span>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
