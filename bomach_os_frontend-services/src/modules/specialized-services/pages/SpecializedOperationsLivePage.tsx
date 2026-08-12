import {
  IconArrowRight,
  IconFilePlus,
  IconPlus,
  IconRefresh,
  IconSettings,
} from '@tabler/icons-react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useMemo } from 'react'

import { useAuth } from '@/app/auth'
import { SectionLoadingState } from '@/app/loading/SectionLoadingState'
import { hasPermission, PERMISSIONS } from '@/app/permissions'
import { serviceRequestQueries } from '@/modules/commercial/api/service-requests.queries'
import { serviceOrderQueries } from '@/modules/fulfillment/service-orders/service-order.queries'
import { serviceAdministrationQueries } from '@/modules/service-administration/api/service-administration.queries'
import type { ServiceCatalogueItem } from '@/modules/service-administration/types/service-administration.types'
import type { AppSectionSearch } from '@/routes/app/$section'
import { presentError } from '@/shared/errors'
import { formatCurrency } from '@/shared/lib/formatters'
import { withoutSearchKeys } from '@/shared/navigation/search-state'
import { ErrorState } from '@/shared/ui'
import { EmptyState } from '@/shared/ui/empty-state'
import {
  CompactActionButton,
  CompactPageToolbar,
  ModulePageFrame,
  ModulePageStatus,
} from '@/shared/ui/module-controls'
import '../styles/specialized-services.css'
import '../../commercial/styles/commercial.css'

const statusClass = (s: string) =>
  s === 'completed' || s === 'converted' || s === 'quoted'
    ? 'commercial-pill-green'
    : s === 'awaiting_client' || s === 'quality_review' || s === 'site_assessment'
      ? 'commercial-pill-yellow'
      : s === 'rejected' || s === 'cancelled' || s === 'on_hold'
        ? 'commercial-pill-gray'
        : 'commercial-pill-blue'
const hasWorkflow = (s: ServiceCatalogueItem) =>
  Boolean(s.activeWorkflow || s.workflowName || s.workflowStages?.length)

export function SpecializedOperationsLivePage({
  recordSearch,
}: {
  recordSearch: AppSectionSearch
}) {
  const { user } = useAuth(),
    navigate = useNavigate()
  const canServices = hasPermission(user, PERMISSIONS.servicesList)
  const canViewService = hasPermission(user, PERMISSIONS.servicesView)
  const canRequests = hasPermission(user, PERMISSIONS.serviceRequestsList)
  const canCreateRequest = hasPermission(user, PERMISSIONS.serviceRequestsCreate)
  const canOrders = hasPermission(user, PERMISSIONS.ordersList)

  const allQ = useQuery({
    ...serviceAdministrationQueries.catalogueList({ status: 'active', limit: 100, offset: 0 }),
    enabled: canServices,
  })
  const divisions = useMemo(
    () =>
      Array.from(
        new Set((allQ.data?.items ?? []).map((x) => x.division.trim()).filter(Boolean)),
      ).sort(),
    [allQ.data?.items],
  )
  const division =
    recordSearch.division && divisions.includes(recordSearch.division)
      ? recordSearch.division
      : (divisions[0] ?? '')
  const divisionQ = useQuery({
    ...serviceAdministrationQueries.catalogueList({
      status: 'active',
      ...(division ? { division } : {}),
      limit: 100,
      offset: 0,
    }),
    enabled: canServices && Boolean(division),
  })
  const services = divisionQ.data?.items ?? []
  const selected = services.find((x) => Number(x.id) === Number(recordSearch.service)) ?? null
  const serviceId = selected ? Number(selected.id) : null
  const detailQ = useQuery({
    ...serviceAdministrationQueries.catalogueDetail(serviceId ?? 0),
    enabled: Boolean(serviceId) && canViewService,
  })
  const requestQ = useQuery({
    ...serviceRequestQueries.list({ serviceId: serviceId ?? 0, page: 1, limit: 10 }),
    enabled: Boolean(serviceId) && canRequests,
  })
  const orderQ = useQuery({
    ...serviceOrderQueries.list({
      ...(selected ? { search: selected.name } : {}),
      page: 1,
      limit: 50,
    }),
    enabled: Boolean(serviceId) && canOrders,
  })
  const orders = useMemo(
    () => (orderQ.data?.items ?? []).filter((x) => x.serviceId === serviceId),
    [orderQ.data?.items, serviceId],
  )
  const detail = detailQ.data ?? selected
  const stages = detail?.activeWorkflow?.stages ?? []
  const activeServices = services.filter((x) => x.status === 'active').length
  const workflows = services.filter(hasWorkflow).length
  const branches = new Set(services.flatMap((x) => x.branchNames)).size
  const avgSla = services.length
    ? Math.round(services.reduce((n, x) => n + (x.slaDays ?? 0), 0) / services.length)
    : 0

  const setContext = (nextDivision: string, nextService?: string) =>
    void navigate({
      to: '/app/$section',
      params: { section: 'survey-engineering-others' },
      search: (p) => ({
        ...withoutSearchKeys(p, ['division', 'service', 'page', 'search', 'status']),
        ...(nextDivision ? { division: nextDivision } : {}),
        ...(nextService ? { service: nextService } : {}),
      }),
      replace: true,
    })
  const refresh = () =>
    Promise.all([
      allQ.refetch(),
      divisionQ.refetch(),
      ...(serviceId
        ? [
            detailQ.refetch(),
            ...(canRequests ? [requestQ.refetch()] : []),
            ...(canOrders ? [orderQ.refetch()] : []),
          ]
        : []),
    ])

  if (allQ.isPending) return <SectionLoadingState section="survey-engineering-others" />
  if (allQ.isError) {
    const e = presentError(allQ.error, 'page-load')
    return (
      <ModulePageStatus
        title="Survey / Engineering / Others"
        breadcrumb="Specialized Services / Operations"
      >
        <ErrorState title={e.title} description={e.message} onRetry={() => void allQ.refetch()} />
      </ModulePageStatus>
    )
  }

  return (
    <ModulePageFrame
      header={
        <CompactPageToolbar
          title="Survey / Engineering / Others"
          breadcrumb="Specialized Services / Operations"
          secondaryAction={
            <CompactActionButton
              disabled={!canCreateRequest}
              locked={!canCreateRequest}
              onClick={() =>
                void navigate({
                  to: '/app/$section',
                  params: { section: 'service-requests' },
                  search: serviceId ? { service: String(serviceId) } : {},
                })
              }
            >
              <IconFilePlus size={14} />
              New Request
            </CompactActionButton>
          }
          primaryAction={
            <CompactActionButton
              tone="primary"
              disabled={!canServices}
              locked={!canServices}
              onClick={() =>
                void navigate({ to: '/app/$section', params: { section: 'service-catalogue' } })
              }
            >
              <IconPlus size={14} />
              Create Service
            </CompactActionButton>
          }
        />
      }
    >
      <main className="specialized-content">
        {division ? (
          <section className="specialized-kpi-grid specialized-kpi-grid--top">
            {[
              ['Active Services', activeServices],
              ['Configured Workflows', workflows],
              ['Branches Covered', branches],
              ['Average SLA', `${avgSla}d`],
            ].map(([l, v]) => (
              <article className="specialized-kpi-card specialized-kpi-card--nt" key={String(l)}>
                <div>{l}</div>
                <strong>{v}</strong>
              </article>
            ))}
          </section>
        ) : null}

        <section className="specialized-card specialized-operations-toolbar">
          <div className="specialized-filter-row specialized-filter-row--compact">
            <label className="specialized-field specialized-specialized-selector">
              <span>Specialized division</span>
              <select value={division} onChange={(e) => setContext(e.target.value)}>
                {divisions.length ? (
                  divisions.map((x) => (
                    <option key={x} value={x}>
                      {x}
                    </option>
                  ))
                ) : (
                  <option value="">No active divisions</option>
                )}
              </select>
            </label>
            <label className="specialized-field specialized-specialized-selector">
              <span>Service</span>
              <select
                value={selected?.id ?? ''}
                disabled={!division}
                onChange={(e) => setContext(division, e.target.value || undefined)}
              >
                <option value="">All Services</option>
                {services.map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.name}
                  </option>
                ))}
              </select>
            </label>
            <span className="specialized-grow" />
            <div className="specialized-action-row">
              <CompactActionButton onClick={() => void refresh()}>
                <IconRefresh size={14} />
                Refresh
              </CompactActionButton>
              <CompactActionButton
                onClick={() =>
                  void navigate({
                    to: '/app/$section',
                    params: { section: 'service-catalogue' },
                    search: selected ? { search: selected.name, division } : { division },
                  })
                }
              >
                <IconSettings size={14} />
                Open Catalogue
              </CompactActionButton>
            </div>
          </div>
        </section>

        {!division ? (
          <EmptyState
            title="No specialized divisions configured"
            description="Active Services with a division appear here automatically from the Service Catalogue."
          />
        ) : (
          <>
            <section className="specialized-card">
              <header className="specialized-card-header">
                <div>
                  <div className="specialized-card-title">Configured Services</div>
                  <div className="specialized-card-subtitle">
                    Live Service Catalogue configuration for {division}
                  </div>
                </div>
                <span className="commercial-count">{services.length} services</span>
              </header>
              {services.length ? (
                <div className="specialized-service-grid specialized-service-grid--scroll">
                  {services.map((s) => (
                    <button
                      key={s.id}
                      className={`specialized-service-card${selected?.id === s.id ? 'is-selected' : ''}`}
                      onClick={() => setContext(division, s.id)}
                    >
                      <b>{s.name}</b>
                      <small>{s.code || 'No code'}</small>
                      <p>{s.description || 'No description configured.'}</p>
                      <div>
                        <span>{s.owner || 'Unassigned'}</span>
                        <span>{s.slaDays ?? 0}d SLA</span>
                        <span>{s.fulfilmentMode || 'No fulfilment mode'}</span>
                        <span>{s.branchNames.length} branches</span>
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <EmptyState
                  title="No Services in this division"
                  description="No active Service Catalogue records are configured for this division."
                />
              )}
            </section>

            {detail ? (
              <div className="specialized-grid-2-1">
                <section className="specialized-card">
                  <header className="specialized-card-header">
                    <div>
                      <div className="specialized-card-title">{detail.name} Lifecycle</div>
                      <div className="specialized-card-subtitle">
                        Configured workflow template — not an individual Order
                      </div>
                    </div>
                  </header>
                  {stages.length ? (
                    <div className="specialized-lifecycle specialized-lifecycle--rail">
                      {stages.map((s, i) => (
                        <article className="specialized-step specialized-step--rail" key={s.id}>
                          <div className="specialized-step-head" aria-hidden="true">
                            <span className="specialized-step-badge">
                              {String(i + 1).padStart(2, '0')}
                            </span>
                          </div>
                          <div className="specialized-step-content">
                            <b>{s.name}</b>
                            <div className="specialized-step-meta">
                              <span>{s.ownerRole || 'Unassigned role'}</span>
                              <span>{Math.round(s.slaHours / 24)}d SLA</span>
                            </div>
                          </div>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <EmptyState
                      title="No active workflow"
                      description="This Service has no active workflow stages configured."
                    />
                  )}
                </section>
                <aside>
                  <section className="specialized-card specialized-card--sticky">
                    <header className="specialized-card-header">
                      <div>
                        <div className="specialized-card-title">Service Control</div>
                      </div>
                    </header>
                    <div className="specialized-control-list">
                      <div>
                        <span>Owner</span>
                        <b>{detail.owner || 'Unassigned'}</b>
                      </div>
                      <div>
                        <span>Default SLA</span>
                        <b>{detail.slaDays ?? 0} days</b>
                      </div>
                      <div>
                        <span>Fulfilment Mode</span>
                        <b>{detail.fulfilmentMode || 'Not configured'}</b>
                      </div>
                      <div>
                        <span>Request Form</span>
                        <b>{detail.requestFormName || 'Not configured'}</b>
                      </div>
                      <div>
                        <span>Pricing</span>
                        <b>{detail.calculatorName || 'Not configured'}</b>
                      </div>
                      <div>
                        <span>Branches</span>
                        <b>{detail.branchNames.length}</b>
                      </div>
                    </div>
                  </section>
                </aside>
              </div>
            ) : (
              <section className="specialized-card">
                <EmptyState
                  title="Select a Service"
                  description="Division mode shows configuration health. Select a Service to see its exact lifecycle and live records."
                />
              </section>
            )}

            {serviceId ? (
              <>
                <div className="specialized-preview-stack">
                  <section className="specialized-card">
                    <header className="specialized-card-header">
                      <div>
                        <div className="specialized-card-title">Live Service Requests</div>
                        <div>
                          <div className="specialized-card-subtitle">
                            Exact backend service filter for {selected?.name}
                          </div>
                        </div>
                      </div>
                      <CompactActionButton
                        onClick={() =>
                          void navigate({
                            to: '/app/$section',
                            params: { section: 'service-requests' },
                            search: { service: String(serviceId) },
                          })
                        }
                      >
                        Open Requests
                        <IconArrowRight size={13} />
                      </CompactActionButton>
                    </header>
                    {!canRequests ? (
                      <div className="specialized-empty">Service Request access not granted.</div>
                    ) : requestQ.data?.items.length ? (
                      <div className="specialized-table-wrap">
                        <table className="specialized-table">
                          <thead>
                            <tr>
                              <th>Request</th>
                              <th>Client</th>
                              <th>Status</th>
                              <th>Priority</th>
                              <th>Owner</th>
                              <th></th>
                            </tr>
                          </thead>
                          <tbody>
                            {requestQ.data.items.map((r) => (
                              <tr key={r.id}>
                                <td>
                                  <b>{r.requestNumber}</b>
                                </td>
                                <td>{r.clientName}</td>
                                <td>
                                  <span className={`commercial-pill ${statusClass(r.status)}`}>
                                    {r.statusDisplay}
                                  </span>
                                </td>
                                <td>{r.priority}</td>
                                <td>{r.ownerName || 'Unassigned'}</td>
                                <td>
                                  <button
                                    className="specialized-btn specialized-btn-small"
                                    onClick={() =>
                                      void navigate({
                                        to: '/app/$section',
                                        params: { section: 'service-requests' },
                                        search: { request: String(r.id) },
                                      })
                                    }
                                  >
                                    Open
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="specialized-empty">No Requests for this Service.</div>
                    )}
                  </section>

                  <section className="specialized-card">
                    <header className="specialized-card-header">
                      <div>
                        <div className="specialized-card-title">Live Order Preview</div>
                        <div className="specialized-card-subtitle">
                          Existing Order search only; authoritative management stays in Service
                          Orders.
                        </div>
                      </div>
                      <CompactActionButton
                        onClick={() =>
                          void navigate({
                            to: '/app/$section',
                            params: { section: 'service-orders' },
                            search: selected ? { search: selected.name } : {},
                          })
                        }
                      >
                        Open Service Orders
                        <IconArrowRight size={13} />
                      </CompactActionButton>
                    </header>
                    {!canOrders ? (
                      <div className="specialized-empty">Service Order access not granted.</div>
                    ) : orders.length ? (
                      <div className="specialized-table-wrap">
                        <table className="specialized-table">
                          <thead>
                            <tr>
                              <th>Order</th>
                              <th>Stage</th>
                              <th>Progress</th>
                              <th>Value</th>
                              <th>Status</th>
                              <th></th>
                            </tr>
                          </thead>
                          <tbody>
                            {orders.map((o) => (
                              <tr key={o.id}>
                                <td>
                                  <b>{o.orderNumber}</b>
                                </td>
                                <td>{o.stage || '—'}</td>
                                <td>{o.progress}%</td>
                                <td>{formatCurrency(o.amount)}</td>
                                <td>
                                  <span className={`commercial-pill ${statusClass(o.orderStatus)}`}>
                                    {o.orderStatus.replaceAll('_', ' ')}
                                  </span>
                                </td>
                                <td>
                                  <button
                                    className="specialized-btn specialized-btn-small"
                                    onClick={() =>
                                      void navigate({
                                        to: '/app/$section',
                                        params: { section: 'service-orders' },
                                        search: { order: String(o.id) },
                                      })
                                    }
                                  >
                                    Open
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="specialized-empty">
                        No exact Service matches returned in the current Order search window.
                      </div>
                    )}
                  </section>
                </div>
              </>
            ) : null}
          </>
        )}
      </main>
    </ModulePageFrame>
  )
}
