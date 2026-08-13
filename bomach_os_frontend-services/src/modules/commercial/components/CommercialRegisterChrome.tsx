import type { ReactNode } from 'react'

interface CommercialSummaryItem {
  label: string
  value: ReactNode
}

interface CommercialSummaryGridProps {
  ariaLabel: string
  items: readonly CommercialSummaryItem[]
  loading?: boolean
  error?: boolean
  errorNote?: string
}

export function CommercialSummaryGrid({
  ariaLabel,
  items,
  loading = false,
  error = false,
  errorNote,
}: CommercialSummaryGridProps) {
  return (
    <section className="commercial-kgrid commercial-kgrid-4" aria-label={ariaLabel}>
      {loading ? (
        <article className="commercial-kpi">
          <div className="commercial-kpi-label">Loading summary...</div>
        </article>
      ) : error ? (
        <article className="commercial-kpi">
          <div className="commercial-kpi-label">Summary unavailable</div>
          {errorNote ? <div className="commercial-kpi-note">{errorNote}</div> : null}
        </article>
      ) : (
        items.map((item) => (
          <article className="commercial-kpi" key={item.label}>
            <div className="commercial-kpi-label">{item.label}</div>
            <div className="commercial-kpi-value">{item.value}</div>
          </article>
        ))
      )}
    </section>
  )
}

interface CommercialRegisterHeaderProps {
  title: string
  description: string
  countLabel: string
  refreshing?: boolean
  action?: ReactNode
}

export function CommercialRegisterHeader({
  title,
  description,
  countLabel,
  refreshing = false,
  action,
}: CommercialRegisterHeaderProps) {
  return (
    <header className="commercial-card-header">
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      <div className="commercial-card-header-actions">
        <span className="commercial-count">{countLabel}</span>
        {refreshing ? <span className="commercial-count">Refreshing…</span> : null}
        {action}
      </div>
    </header>
  )
}
