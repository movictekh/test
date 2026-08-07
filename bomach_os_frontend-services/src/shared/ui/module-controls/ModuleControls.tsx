import { IconSearch } from '@tabler/icons-react'
import type { ReactNode } from 'react'

import { cn } from '@/shared/lib/cn'

export function CompactPageToolbar({
  title,
  breadcrumb,
  primaryAction,
  secondaryAction,
}: {
  title: string
  breadcrumb: string
  primaryAction?: ReactNode
  secondaryAction?: ReactNode
}) {
  return (
    <section className="border-border bg-surface sticky top-0 z-20 flex min-h-[58px] flex-col gap-2 border-b px-3 py-2.5 sm:flex-row sm:items-center sm:justify-between lg:px-5">
      <div className="min-w-0 flex-1">
        <h1 className="text-foreground truncate text-[0.875rem] leading-tight font-extrabold">
          {title}
        </h1>
        <p className="text-foreground-subtle mt-0.5 truncate text-[0.53125rem] font-medium">
          {breadcrumb}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        {secondaryAction}
        {primaryAction}
      </div>
    </section>
  )
}

export function CompactActionButton({
  children,
  onClick,
  tone = 'secondary',
  type = 'button',
  disabled,
}: {
  children: ReactNode
  onClick?: () => void
  tone?: 'primary' | 'secondary' | 'ghost'
  type?: 'button' | 'submit'
  disabled?: boolean
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'rounded-control inline-flex h-7 items-center justify-center gap-1.5 px-2.5 text-[0.625rem] font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50',
        tone === 'primary' && 'bg-brand-600 hover:bg-brand-800 text-white',
        tone === 'secondary' &&
          'border-border bg-surface text-foreground hover:bg-surface-muted border',
        tone === 'ghost' && 'text-foreground hover:bg-surface-muted',
      )}
    >
      {children}
    </button>
  )
}

export function SummaryStrip({
  items,
}: {
  items: { label: string; value: number | string; note?: string }[]
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
      {items.map((item) => (
        <article
          key={item.label}
          className="border-border bg-surface rounded-card border px-3 py-2.5"
        >
          <p className="text-foreground-subtle text-[0.5625rem] font-bold tracking-[0.08em] uppercase">
            {item.label}
          </p>
          <p className="text-foreground mt-1 text-lg font-extrabold">{item.value}</p>
          {item.note ? (
            <p className="text-foreground-subtle mt-0.5 text-[0.5625rem]">{item.note}</p>
          ) : null}
        </article>
      ))}
    </div>
  )
}

export function FilterBar({
  search,
  onSearch,
  children,
}: {
  search: string
  onSearch: (value: string) => void
  children?: ReactNode
}) {
  return (
    <div className="border-border bg-surface rounded-card flex flex-col gap-2 border p-2.5 lg:flex-row lg:items-center">
      <label className="border-border bg-surface-muted flex h-8 min-w-0 flex-1 items-center gap-2 rounded-lg border px-2.5">
        <IconSearch size={14} className="text-foreground-subtle" />
        <input
          value={search}
          onChange={(event) => onSearch(event.target.value)}
          placeholder="Search"
          className="min-w-0 flex-1 bg-transparent text-[0.6875rem] outline-none"
        />
      </label>
      <div className="flex flex-wrap items-center gap-1.5">{children}</div>
    </div>
  )
}

export function FilterSelect({
  value,
  onChange,
  children,
  label,
}: {
  value: string
  onChange: (value: string) => void
  children: ReactNode
  label: string
}) {
  return (
    <label className="border-border bg-surface inline-flex h-8 items-center gap-1.5 rounded-lg border px-2.5">
      <span className="text-foreground-subtle text-[0.5625rem] font-bold uppercase">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="bg-transparent text-[0.625rem] font-semibold outline-none"
      >
        {children}
      </select>
    </label>
  )
}
