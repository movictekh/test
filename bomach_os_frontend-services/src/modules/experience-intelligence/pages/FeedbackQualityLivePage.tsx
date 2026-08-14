import {
  IconFilePlus,
  IconMessageStar,
  IconPlus,
  IconRefresh,
  IconSearch,
} from '@tabler/icons-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '@/app/auth'
import { SectionLoadingState } from '@/app/loading/SectionLoadingState'
import { hasPermission, PERMISSIONS } from '@/app/permissions'
import type { AppSectionSearch } from '@/routes/app/$section'
import { presentError } from '@/shared/errors'
import { withOptionalSearchValue, withoutSearchKeys } from '@/shared/navigation/search-state'
import { ErrorState, useToast } from '@/shared/ui'
import { EmptyState } from '@/shared/ui/empty-state'
import {
  CompactActionButton,
  CompactPageToolbar,
  ModulePageFrame,
  ModulePageStatus,
} from '@/shared/ui/module-controls'
import { feedbackApi } from '../feedback/feedback.api'
import { feedbackKeys } from '../feedback/feedback.keys'
import { feedbackQueries } from '../feedback/feedback.queries'
import {
  feedbackStatusOptions,
  feedbackTypeOptions,
  type FeedbackStatus,
  type FeedbackType,
  type UpdateQualityFollowUpInput,
} from '../feedback/feedback.types'
import { FeedbackQualityFollowUpWorkspace } from '../workspaces/FeedbackQualityFollowUpWorkspace'
import { RecordClientFeedbackWorkspace } from '../workspaces/RecordClientFeedbackWorkspace'
import '../styles/experience-intelligence.css'
const sc = (s: FeedbackStatus) =>
  s === 'closed'
    ? 'experience-pill-green'
    : s === 'action_required'
      ? 'experience-pill-red'
      : 'experience-pill-yellow'
const stars = (n: number) => {
  const r = Math.max(0, Math.min(5, Math.round(n)))
  return `${'★'.repeat(r)}${'☆'.repeat(5 - r)}`
}
const dl = (v: string) => {
  if (!v) return '—'
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? v : d.toLocaleDateString()
}
export function FeedbackQualityLivePage({ recordSearch }: { recordSearch: AppSectionSearch }) {
  const { user } = useAuth(),
    navigate = useNavigate(),
    qc = useQueryClient(),
    toast = useToast()
  const canList = hasPermission(user, PERMISSIONS.feedbackList),
    canView = hasPermission(user, PERMISSIONS.feedbackView),
    canCreate = hasPermission(user, PERMISSIONS.feedbackCreate),
    canUpdate = hasPermission(user, PERMISSIONS.feedbackUpdate)
  const [searchDraft, setSearchDraft] = useState(recordSearch.search ?? ''),
    [synced, setSynced] = useState(recordSearch.search ?? ''),
    [recordOpen, setRecordOpen] = useState(false)
  const id = recordSearch.feedback ? Number(recordSearch.feedback) : null
  const feedbackType = (recordSearch.feedbackType ?? '') as FeedbackType | '',
    status = (recordSearch.status ?? '') as FeedbackStatus | '',
    ratingMin = recordSearch.ratingMin ? Number(recordSearch.ratingMin) : null
  const filters = useMemo(
    () => ({
      ...(recordSearch.search ? { search: recordSearch.search } : {}),
      ...(status ? { status } : {}),
      ...(feedbackType ? { feedbackType } : {}),
      ...(ratingMin ? { ratingMin } : {}),
    }),
    [recordSearch.search, status, feedbackType, ratingMin],
  )
  const listQ = useQuery({ ...feedbackQueries.list(filters), enabled: canList }),
    statsQ = useQuery({ ...feedbackQueries.stats(), enabled: canList }),
    detailQ = useQuery({ ...feedbackQueries.detail(id ?? 0), enabled: Boolean(id) && canView })
  const update = useMutation({
    mutationFn: ({ id, input }: { id: number; input: UpdateQualityFollowUpInput }) =>
      feedbackApi.updateQualityFollowUp(id, input),
    onSuccess: async (f) => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: feedbackKeys.lists() }),
        qc.invalidateQueries({ queryKey: feedbackKeys.stats() }),
        qc.invalidateQueries({ queryKey: feedbackKeys.detail(f.id) }),
      ])
      toast.success('Quality follow-up updated')
    },
    onError: (e) =>
      toast.error('Quality follow-up could not be updated', {
        description: presentError(e, 'background-action').message,
      }),
  })
  const create = useMutation({
    mutationFn: feedbackApi.create,
    onSuccess: async (f) => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: feedbackKeys.lists() }),
        qc.invalidateQueries({ queryKey: feedbackKeys.stats() }),
        qc.invalidateQueries({ queryKey: feedbackKeys.detail(f.id) }),
      ])
      setRecordOpen(false)
      toast.success('Client feedback recorded')
    },
    onError: (e) =>
      toast.error('Client feedback could not be recorded', {
        description: presentError(e, 'form-submit').message,
      }),
  })
  const setValue = useCallback(
    function <K extends keyof AppSectionSearch>(key: K, value: AppSectionSearch[K] | '' | null) {
      void navigate({
        to: '/app/$section',
        params: { section: 'feedback-quality' },
        search: (p) => ({
          ...withoutSearchKeys(p, [key]),
          ...withOptionalSearchValue<AppSectionSearch, K>(key, value),
        }),
        replace: true,
      })
    },
    [navigate],
  )
  if ((recordSearch.search ?? '') !== synced) {
    setSynced(recordSearch.search ?? '')
    setSearchDraft(recordSearch.search ?? '')
  }
  useEffect(() => {
    if (searchDraft === (recordSearch.search ?? '')) return
    const t = window.setTimeout(() => setValue('search', searchDraft), 350)
    return () => window.clearTimeout(t)
  }, [recordSearch.search, searchDraft, setValue])
  const clear = () => {
    setSearchDraft('')
    void navigate({
      to: '/app/$section',
      params: { section: 'feedback-quality' },
      search: (p) => withoutSearchKeys(p, ['search', 'status', 'feedbackType', 'ratingMin']),
      replace: true,
    })
  }
  const refresh = async () => {
    await Promise.all([
      listQ.refetch(),
      statsQ.refetch(),
      ...(id && canView ? [detailQ.refetch()] : []),
    ])
    toast.success('Feedback & Quality refreshed')
  }
  if (!canList)
    return (
      <ModulePageStatus title="Feedback & Quality" breadcrumb="Client experience / Quality">
        <ErrorState
          title="Feedback access not granted"
          description="You do not have permission to list client feedback."
        />
      </ModulePageStatus>
    )
  if (listQ.isPending || statsQ.isPending) return <SectionLoadingState section="feedback-quality" />
  if (listQ.isError || statsQ.isError) {
    const e = presentError(listQ.error ?? statsQ.error, 'page-load')
    return (
      <ModulePageStatus title="Feedback & Quality" breadcrumb="Client experience / Quality">
        <ErrorState
          title={e.title}
          description={e.message}
          onRetry={() => {
            void listQ.refetch()
            void statsQ.refetch()
          }}
        />
      </ModulePageStatus>
    )
  }
  const rows = listQ.data,
    stats = statsQ.data,
    hasFilters = Boolean(recordSearch.search || status || feedbackType || ratingMin)
  return (
    <ModulePageFrame
      header={
        <CompactPageToolbar
          title="Feedback & Quality"
          breadcrumb="Client experience / Quality"
          secondaryAction={
            <CompactActionButton
              onClick={() =>
                void navigate({
                  to: '/app/$section',
                  params: { section: 'service-requests' },
                  search: { create: 'request' },
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
      <main className="experience-content">
        <section className="experience-kpi-grid">
          <article className="experience-kpi-card">
            <div>Average rating</div>
            <strong>{stats.averageRating.toFixed(1)}/5</strong>
          </article>
          <article className="experience-kpi-card">
            <div>Client satisfaction</div>
            <strong>{stats.clientSatisfaction.toFixed(1)}%</strong>
          </article>
          <article className="experience-kpi-card">
            <div>Rework rate</div>
            <strong>{stats.reworkRate.toFixed(1)}%</strong>
          </article>
          <article className="experience-kpi-card">
            <div>Repeat clients</div>
            <strong>{stats.repeatClients.toFixed(1)}%</strong>
          </article>
        </section>
        <section className="experience-card">
          <header className="experience-card-header">
            <div>
              <div className="experience-card-title">Service Feedback Register</div>
              <div className="experience-card-subtitle">
                Client feedback, complaints, defects, testimonials and internal quality follow-up
              </div>
            </div>
            <div className="experience-card-header-actions">
              <span className="experience-count">
                {rows.length} feedback record{rows.length === 1 ? '' : 's'}
              </span>
              {listQ.isFetching ? <span className="experience-count">Refreshing…</span> : null}
            </div>
          </header>
          <div className="experience-filter-row experience-filter-row--actions">
            <div className="experience-card-header-actions">
              <button
                className="experience-btn"
                type="button"
                disabled={listQ.isFetching || statsQ.isFetching}
                onClick={() => void refresh()}
              >
                <IconRefresh size={14} />
                Refresh
              </button>
              {canCreate ? (
                <button
                  className="experience-btn experience-btn-primary"
                  type="button"
                  onClick={() => setRecordOpen(true)}
                >
                  <IconMessageStar size={14} />
                  Record Client Feedback
                </button>
              ) : null}
            </div>
          </div>
          <div className="experience-filter-row">
            <label className="experience-search">
              <IconSearch size={14} />
              <input
                value={searchDraft}
                placeholder="Search client, service or comment"
                onChange={(e) => setSearchDraft(e.target.value)}
              />
            </label>
            <select value={status} onChange={(e) => setValue('status', e.target.value)}>
              <option value="">All statuses</option>
              {feedbackStatusOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            <select value={feedbackType} onChange={(e) => setValue('feedbackType', e.target.value)}>
              <option value="">All feedback types</option>
              {feedbackTypeOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            <select
              value={ratingMin ?? ''}
              onChange={(e) =>
                setValue('ratingMin', e.target.value ? Number(e.target.value) : null)
              }
            >
              <option value="">Any rating</option>
              <option value="5">5 only</option>
              <option value="4">4+</option>
              <option value="3">3+</option>
              <option value="2">2+</option>
              <option value="1">1+</option>
            </select>
            {hasFilters ? (
              <button className="experience-btn" type="button" onClick={clear}>
                Clear
              </button>
            ) : null}
          </div>
          {rows.length ? (
            <div className="experience-table-wrap">
              <table className="experience-table experience-feedback-table">
                <thead>
                  <tr>
                    <th>Feedback</th>
                    <th>Client</th>
                    <th>Service</th>
                    <th>Order</th>
                    <th>Rating</th>
                    <th>Type</th>
                    <th>Comment</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((x) => (
                    <tr
                      key={x.id}
                      className="experience-clickable-row"
                      tabIndex={canView ? 0 : -1}
                      onClick={() => {
                        if (canView) setValue('feedback', String(x.id))
                      }}
                      onKeyDown={(e) => {
                        if (!canView || (e.key !== 'Enter' && e.key !== ' ')) return
                        e.preventDefault()
                        setValue('feedback', String(x.id))
                      }}
                    >
                      <td>
                        <b>FDB-{String(x.id).padStart(5, '0')}</b>
                        <div className="experience-row-sub">{dl(x.createdAt)}</div>
                      </td>
                      <td>{x.clientName}</td>
                      <td>{x.serviceName}</td>
                      <td>
                        <button
                          className="experience-link-button"
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            void navigate({
                              to: '/app/$section',
                              params: { section: 'service-orders' },
                              search: { order: String(x.orderId) },
                            })
                          }}
                        >
                          {x.orderNumber || `#${x.orderId}`}
                        </button>
                      </td>
                      <td>
                        <span className="experience-rating">{stars(x.rating)}</span>
                        <small>{x.rating}/5</small>
                      </td>
                      <td>{x.feedbackTypeDisplay}</td>
                      <td className="experience-comment-cell">{x.comment}</td>
                      <td>
                        <span className={`experience-pill ${sc(x.status)}`}>{x.statusDisplay}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              title={hasFilters ? 'No matching feedback' : 'No feedback recorded'}
              description={
                hasFilters
                  ? 'Adjust or clear the current Feedback filters.'
                  : 'Client feedback will appear here when records are available.'
              }
            />
          )}
        </section>
      </main>
      {recordOpen && canCreate ? (
        <RecordClientFeedbackWorkspace
          initialOrderId={recordSearch.order ? Number(recordSearch.order) : null}
          saving={create.isPending}
          onClose={() => setRecordOpen(false)}
          onSubmit={(input) => create.mutate(input)}
        />
      ) : null}
      {id && canView && detailQ.data ? (
        <FeedbackQualityFollowUpWorkspace
          feedback={detailQ.data}
          canUpdate={canUpdate}
          saving={update.isPending}
          onClose={() => setValue('feedback', null)}
          onSave={(input) => update.mutate({ id: detailQ.data.id, input })}
        />
      ) : null}
    </ModulePageFrame>
  )
}
