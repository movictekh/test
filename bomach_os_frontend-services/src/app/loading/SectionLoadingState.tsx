import type { CSSProperties } from 'react'

import { ModulePageStatus } from '@/shared/ui/module-controls'

import './section-loading.css'

type LoadingFamily = 'register' | 'analytics' | 'board' | 'builder'

type SectionLoadingDefinition = {
  title: string
  breadcrumb: string
  family: LoadingFamily
  kpis?: number
  filters?: number
  columns?: number
}

type OptionalKpis = {
  kpis?: number
}

type OptionalRegisterMetrics = {
  kpis?: number
  filters?: number
  columns?: number
}

const definitions: Record<string, SectionLoadingDefinition> = {
  'service-catalogue': {
    title: 'Service Catalogue',
    breadcrumb: 'Services / Setup and activation',
    family: 'builder',
    kpis: 4,
  },
  'calculator-library': {
    title: 'Calculator Library',
    breadcrumb: 'Services / Pricing engine',
    family: 'builder',
    kpis: 3,
  },
  'request-form-builder': {
    title: 'Request Form Builder',
    breadcrumb: 'Services / Form design',
    family: 'builder',
    kpis: 3,
  },
  'workflow-designer': {
    title: 'Workflow Designer',
    breadcrumb: 'Services / Fulfillment automation',
    family: 'builder',
    kpis: 3,
  },
  'branch-activation': {
    title: 'Branch Activation',
    breadcrumb: 'Services / Availability and capacity',
    family: 'builder',
    kpis: 3,
  },
  'service-requests': {
    title: 'Service Requests',
    breadcrumb: 'Commercial flow / Requests',
    family: 'register',
    kpis: 4,
    filters: 5,
    columns: 9,
  },
  quotations: {
    title: 'Quotations & Proposals',
    breadcrumb: 'Commercial flow / Offers',
    family: 'register',
    kpis: 4,
    filters: 2,
    columns: 8,
  },
  'invoices-payments': {
    title: 'Invoices & Payments',
    breadcrumb: 'Commercial flow / Billing',
    family: 'register',
    kpis: 4,
    filters: 4,
    columns: 8,
  },
  approvals: {
    title: 'Approvals',
    breadcrumb: 'Commercial flow / Governance',
    family: 'register',
    kpis: 4,
    filters: 3,
    columns: 7,
  },
  'service-orders': {
    title: 'Service Orders',
    breadcrumb: 'Fulfillment / Orders',
    family: 'register',
    kpis: 4,
    filters: 4,
    columns: 9,
  },
  'execution-tasks': {
    title: 'Execution Tasks',
    breadcrumb: 'Fulfillment / Execution',
    family: 'register',
    kpis: 4,
    filters: 4,
    columns: 8,
  },
  deliverables: {
    title: 'Deliverables',
    breadcrumb: 'Fulfillment / Deliverables',
    family: 'register',
    kpis: 4,
    filters: 4,
    columns: 8,
  },
  'feedback-quality': {
    title: 'Feedback & Quality',
    breadcrumb: 'Experience / Quality control',
    family: 'register',
    kpis: 4,
    filters: 4,
    columns: 7,
  },
  'reports-analytics': {
    title: 'Reports & Analytics',
    breadcrumb: 'Intelligence / Performance',
    family: 'analytics',
    kpis: 4,
  },
  'real-estate-inventory': {
    title: 'Real Estate Inventory',
    breadcrumb: 'Specialized Services / Real Estate',
    family: 'board',
    kpis: 4,
  },
  'survey-engineering-others': {
    title: 'Survey / Engineering / Others',
    breadcrumb: 'Specialized Services / Operations',
    family: 'analytics',
    kpis: 4,
  },
}

function SkeletonBlock({ className = '', style }: { className?: string; style?: CSSProperties }) {
  return <span aria-hidden="true" className={`section-loading-block ${className}`} style={style} />
}

function ToolbarSkeleton() {
  return (
    <div className="section-loading-toolbar-actions" aria-hidden="true">
      <SkeletonBlock className="section-loading-button" />
      <SkeletonBlock className="section-loading-button section-loading-button--primary" />
    </div>
  )
}

function KpiSkeleton({ count }: { count: number }) {
  return (
    <section
      className="section-loading-kpis"
      style={{ '--section-loading-count': count } as CSSProperties}
      aria-hidden="true"
    >
      {Array.from({ length: count }, (_, index) => (
        <article className="section-loading-card section-loading-kpi" key={index}>
          <SkeletonBlock className="section-loading-line section-loading-line--sm" />
          <SkeletonBlock className="section-loading-value" />
          <SkeletonBlock className="section-loading-line section-loading-line--xs" />
        </article>
      ))}
    </section>
  )
}

function FilterSkeleton({ count }: { count: number }) {
  return (
    <div className="section-loading-filters" aria-hidden="true">
      {Array.from({ length: count }, (_, index) => (
        <SkeletonBlock
          className={
            index === 0
              ? 'section-loading-filter section-loading-filter--search'
              : 'section-loading-filter'
          }
          key={index}
        />
      ))}
    </div>
  )
}

function TableSkeleton({ columns = 7, rows = 6 }: { columns?: number; rows?: number }) {
  return (
    <div className="section-loading-table" aria-hidden="true">
      <div
        className="section-loading-table-row section-loading-table-row--head"
        style={{ '--section-loading-columns': columns } as CSSProperties}
      >
        {Array.from({ length: columns }, (_, index) => (
          <SkeletonBlock className="section-loading-table-cell" key={index} />
        ))}
      </div>
      {Array.from({ length: rows }, (_, row) => (
        <div
          className="section-loading-table-row"
          style={{ '--section-loading-columns': columns } as CSSProperties}
          key={row}
        >
          {Array.from({ length: columns }, (_, column) => (
            <SkeletonBlock
              className={`section-loading-table-cell section-loading-table-cell--${(column + row) % 3}`}
              key={column}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

function RegisterSkeleton({ kpis = 4, filters = 4, columns = 7 }: OptionalRegisterMetrics) {
  return (
    <>
      {kpis ? <KpiSkeleton count={kpis} /> : null}
      <section className="section-loading-card section-loading-register">
        <div className="section-loading-card-head" aria-hidden="true">
          <div>
            <SkeletonBlock className="section-loading-line section-loading-line--title" />
            <SkeletonBlock className="section-loading-line section-loading-line--medium" />
          </div>
          <SkeletonBlock className="section-loading-button" />
        </div>
        <FilterSkeleton count={filters ?? 4} />
        <TableSkeleton columns={columns} />
      </section>
    </>
  )
}

function AnalyticsSkeleton({ kpis = 4 }: OptionalKpis) {
  return (
    <>
      <KpiSkeleton count={kpis ?? 4} />
      <div className="section-loading-grid-2">
        <section className="section-loading-card">
          <div className="section-loading-card-head" aria-hidden="true">
            <div>
              <SkeletonBlock className="section-loading-line section-loading-line--title" />
              <SkeletonBlock className="section-loading-line section-loading-line--medium" />
            </div>
            <SkeletonBlock className="section-loading-button" />
          </div>
          <div className="section-loading-metrics" aria-hidden="true">
            {Array.from({ length: 5 }, (_, index) => (
              <div className="section-loading-metric" key={index}>
                <SkeletonBlock className="section-loading-line section-loading-line--medium" />
                <SkeletonBlock className="section-loading-progress" />
                <SkeletonBlock className="section-loading-line section-loading-line--xs" />
              </div>
            ))}
          </div>
        </section>
        <section className="section-loading-card">
          <div className="section-loading-card-head" aria-hidden="true">
            <div>
              <SkeletonBlock className="section-loading-line section-loading-line--title" />
              <SkeletonBlock className="section-loading-line section-loading-line--medium" />
            </div>
          </div>
          <TableSkeleton columns={5} rows={5} />
        </section>
      </div>
    </>
  )
}

function BoardSkeleton({ kpis = 4 }: OptionalKpis) {
  return (
    <>
      <KpiSkeleton count={kpis ?? 4} />
      <section className="section-loading-card">
        <div className="section-loading-card-head" aria-hidden="true">
          <div>
            <SkeletonBlock className="section-loading-line section-loading-line--title" />
            <SkeletonBlock className="section-loading-line section-loading-line--medium" />
          </div>
          <div className="section-loading-toolbar-actions">
            <SkeletonBlock className="section-loading-button" />
            <SkeletonBlock className="section-loading-button" />
            <SkeletonBlock className="section-loading-button section-loading-button--primary" />
          </div>
        </div>
        <FilterSkeleton count={2} />
      </section>
      <div className="section-loading-board-grid">
        <section className="section-loading-card">
          <div className="section-loading-card-head" aria-hidden="true">
            <div>
              <SkeletonBlock className="section-loading-line section-loading-line--title" />
              <SkeletonBlock className="section-loading-line section-loading-line--medium" />
            </div>
          </div>
          <div className="section-loading-board" aria-hidden="true">
            {Array.from({ length: 30 }, (_, index) => (
              <SkeletonBlock className="section-loading-tile" key={index} />
            ))}
          </div>
        </section>
        <aside className="section-loading-card section-loading-side" aria-hidden="true">
          <SkeletonBlock className="section-loading-line section-loading-line--title" />
          {Array.from({ length: 7 }, (_, index) => (
            <SkeletonBlock className="section-loading-field" key={index} />
          ))}
          <SkeletonBlock className="section-loading-button section-loading-button--wide" />
        </aside>
      </div>
    </>
  )
}

function BuilderSkeleton({ kpis = 3 }: OptionalKpis) {
  return (
    <>
      <KpiSkeleton count={kpis ?? 3} />
      <div className="section-loading-builder-grid">
        <section className="section-loading-card">
          <div className="section-loading-card-head" aria-hidden="true">
            <div>
              <SkeletonBlock className="section-loading-line section-loading-line--title" />
              <SkeletonBlock className="section-loading-line section-loading-line--medium" />
            </div>
            <SkeletonBlock className="section-loading-button section-loading-button--primary" />
          </div>
          <FilterSkeleton count={3} />
          <TableSkeleton columns={6} rows={7} />
        </section>
        <aside className="section-loading-card section-loading-side" aria-hidden="true">
          <SkeletonBlock className="section-loading-line section-loading-line--title" />
          <SkeletonBlock className="section-loading-line section-loading-line--medium" />
          {Array.from({ length: 6 }, (_, index) => (
            <SkeletonBlock className="section-loading-field" key={index} />
          ))}
        </aside>
      </div>
    </>
  )
}

function loadingBody(definition: SectionLoadingDefinition) {
  switch (definition.family) {
    case 'analytics':
      return (
        <AnalyticsSkeleton {...(definition.kpis !== undefined ? { kpis: definition.kpis } : {})} />
      )
    case 'board':
      return <BoardSkeleton {...(definition.kpis !== undefined ? { kpis: definition.kpis } : {})} />
    case 'builder':
      return (
        <BuilderSkeleton {...(definition.kpis !== undefined ? { kpis: definition.kpis } : {})} />
      )
    case 'register':
    default:
      return (
        <RegisterSkeleton
          {...(definition.kpis !== undefined ? { kpis: definition.kpis } : {})}
          {...(definition.filters !== undefined ? { filters: definition.filters } : {})}
          {...(definition.columns !== undefined ? { columns: definition.columns } : {})}
        />
      )
  }
}

export function SectionLoadingState({ section }: { section: string }) {
  const definition =
    definitions[section] ??
    ({
      title: section
        .split('-')
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(' '),
      breadcrumb: 'Service Operations',
      family: 'register',
      filters: 3,
      columns: 6,
    } satisfies SectionLoadingDefinition)

  return (
    <ModulePageStatus title={definition.title} breadcrumb={definition.breadcrumb}>
      <div
        className="section-loading-root"
        aria-label={`${definition.title} loading`}
        aria-busy="true"
      >
        <ToolbarSkeleton />
        {loadingBody(definition)}
      </div>
    </ModulePageStatus>
  )
}
