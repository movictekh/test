import { IconX } from '@tabler/icons-react'
import { useState, type FormEvent } from 'react'

import { useToast } from '@/shared/ui'
import { formatCurrency } from '@/shared/lib/formatters'

import type { CommercialServiceRequest, ServiceRequestStatus } from '../types/commercial.types'
import type { UpdateServiceRequestInput } from '../api/commercial.api'

const lifecycle = [
  'Request',
  'Review',
  'Assessment',
  'Quote',
  'Approval',
  'Invoice',
  'Order',
  'Fulfillment',
] as const

const controlStatuses: ServiceRequestStatus[] = [
  'New',
  'Under Review',
  'Awaiting Client',
  'Site Assessment',
  'Quoted',
  'Converted',
  'Rejected',
]

const activityTypes = [
  'Phone call',
  'WhatsApp',
  'Email',
  'Meeting',
  'Site assessment',
  'Internal note',
  'Document received',
] as const

const activityOutcomes = [
  'Successful',
  'No response',
  'Information required',
  'Follow-up scheduled',
  'Escalated',
] as const

function statusClass(status: string) {
  if (status === 'New' || status === 'Rejected') return 'commercial-pill-gray'
  if (status === 'Quoted' || status === 'Converted') return 'commercial-pill-green'
  if (status === 'Awaiting Client' || status === 'Site Assessment') return 'commercial-pill-yellow'
  return 'commercial-pill-blue'
}

function lifecycleActiveIndex(status: string) {
  if (status === 'New') return 0
  if (status === 'Under Review' || status === 'Awaiting Client') return 1
  if (status === 'Site Assessment') return 2
  if (status === 'Awaiting Quotation' || status === 'Quoted') return 3
  if (status === 'Client Approval') return 4
  if (status === 'Converted') return 6
  return 2
}

export function Request360Workspace({
  request,
  saving,
  onClose,
  onUpdate,
  onPrepareQuotation,
}: {
  request: CommercialServiceRequest
  saving: boolean
  onClose: () => void
  onUpdate: (requestId: string, input: UpdateServiceRequestInput) => void
  onPrepareQuotation: (requestId: string) => void
}) {
  const toast = useToast()
  const [status, setStatus] = useState(request.status)
  const [owner, setOwner] = useState(request.owner)
  const [nextAction, setNextAction] = useState(request.nextAction)
  const [dueAt, setDueAt] = useState(request.dueAt)
  const [activityOpen, setActivityOpen] = useState(false)
  const [activityType, setActivityType] = useState<string>(activityTypes[0])
  const [activityOutcome, setActivityOutcome] = useState<string>(activityOutcomes[0])
  const [activityNote, setActivityNote] = useState('')
  const [activityNext, setActivityNext] = useState('')

  const activeStage = lifecycleActiveIndex(request.status)
  const lead = request.intakeResponses['Lead / campaign reference']
  const activities = [...request.activities].reverse()

  const saveControl = () => {
    onUpdate(request.id, {
      status,
      owner: owner.trim() || request.owner,
      nextAction: nextAction.trim() || request.nextAction,
      dueAt,
      activity: {
        at: new Date().toISOString(),
        title: 'Control update',
        actor: 'Commercial Operations',
        description: `Status: ${status}; next: ${nextAction.trim() || request.nextAction}`,
      },
    })
    toast.success('Request updated')
  }

  const scheduleAssessment = () => {
    onUpdate(request.id, {
      status: 'Site Assessment',
      nextAction: 'Attend assessment and upload findings',
      activity: {
        at: new Date().toISOString(),
        title: 'Assessment scheduled',
        actor: 'Commercial Operations',
        description: 'Technical assessment task created.',
      },
    })
    toast.success('Assessment task created')
  }

  const convertToOrder = () => {
    onUpdate(request.id, {
      status: 'Converted',
      nextAction: `Track order from ${request.id}`,
      activity: {
        at: new Date().toISOString(),
        title: 'Converted to service order',
        actor: 'Commercial Operations',
        description: `Service order created from ${request.id}.`,
      },
    })
    toast.success('Service order created')
    onClose()
  }

  const saveActivity = (event: FormEvent) => {
    event.preventDefault()
    onUpdate(request.id, {
      ...(activityNext.trim() ? { nextAction: activityNext.trim() } : {}),
      activity: {
        at: new Date().toISOString(),
        title: activityType,
        actor: 'Commercial Operations',
        description: `${activityOutcome}: ${activityNote.trim() || 'No additional note.'}`,
      },
    })
    setActivityOpen(false)
    setActivityNote('')
    setActivityNext('')
    toast.success('Activity recorded')
  }

  return (
    <>
      <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
        <section
          className="commercial-modal commercial-modal--xl commercial-request360"
          role="dialog"
          aria-modal="true"
          aria-label={`Request 360 File — ${request.id}`}
          onMouseDown={(event) => event.stopPropagation()}
        >
          <header className="commercial-modal-header">
            <h2>Request 360 File — {request.id}</h2>
            <button
              type="button"
              className="commercial-modal-close"
              onClick={onClose}
              aria-label="Close"
            >
              <IconX size={16} />
            </button>
          </header>

          <div className="commercial-modal-body">
            <div className="commercial-g21">
              <div className="commercial-g21-main">
                <section className="commercial-card commercial-request360-card">
                  <div className="commercial-card-header">
                    <div>
                      <h2>{request.client}</h2>
                      <p>
                        {request.service} · {request.branch} · {request.createdAt}
                      </p>
                    </div>
                    <span className={`commercial-pill ${statusClass(request.status)}`}>
                      {request.status}
                    </span>
                  </div>
                  <div className="commercial-life">
                    {lifecycle.map((stage, index) => (
                      <article
                        key={stage}
                        className={[
                          'commercial-step',
                          index < activeStage ? 'commercial-step--done' : '',
                          index === activeStage ? 'commercial-step--active' : '',
                        ]
                          .filter(Boolean)
                          .join(' ')}
                      >
                        <small>{String(index + 1).padStart(2, '0')}</small>
                        <b>{stage}</b>
                        <span>
                          {index < activeStage
                            ? 'Completed'
                            : index === activeStage
                              ? 'In progress'
                              : 'Pending'}
                        </span>
                      </article>
                    ))}
                  </div>
                </section>

                <section className="commercial-card commercial-request360-card">
                  <div className="commercial-card-header">
                    <div>
                      <h2>Request Information</h2>
                      <p>Permanent client and commercial record</p>
                    </div>
                  </div>
                  <div className="commercial-info-grid">
                    <div>
                      <div className="commercial-kl">Client</div>
                      <b>{request.client}</b>
                    </div>
                    <div>
                      <div className="commercial-kl">Phone</div>
                      <b>{request.phone || '—'}</b>
                    </div>
                    <div>
                      <div className="commercial-kl">Customer type</div>
                      <b>{request.clientType}</b>
                    </div>
                    <div>
                      <div className="commercial-kl">Source / Lead</div>
                      <b>
                        {request.source}
                        {lead ? ` · ${lead}` : ''}
                      </b>
                    </div>
                    <div>
                      <div className="commercial-kl">Budget</div>
                      <b>{formatCurrency(request.budget)}</b>
                    </div>
                    <div>
                      <div className="commercial-kl">Estimate</div>
                      <b>{formatCurrency(request.estimate)}</b>
                    </div>
                    <div className="commercial-info-full">
                      <div className="commercial-kl">Scope / Request</div>
                      <p>{request.details}</p>
                    </div>
                  </div>
                </section>

                <section className="commercial-card commercial-request360-card">
                  <div className="commercial-card-header">
                    <div>
                      <h2>Activity & Communication Journal</h2>
                      <p>Calls, WhatsApp, email, meetings, site visits and decisions</p>
                    </div>
                    <button
                      type="button"
                      className="commercial-btn commercial-btn-primary"
                      onClick={() => setActivityOpen(true)}
                    >
                      Add Activity
                    </button>
                  </div>
                  <div className="commercial-timeline-list">
                    {activities.length === 0 ? (
                      <div className="commercial-empty">No activity recorded.</div>
                    ) : (
                      activities.map((activity) => (
                        <article key={activity.id} className="commercial-tl">
                          <b>{activity.title}</b>
                          <p>
                            {activity.description}
                            <br />
                            <strong>{activity.actor}</strong>
                          </p>
                          <time>{new Date(activity.at).toLocaleString('en-GB')}</time>
                        </article>
                      ))
                    )}
                  </div>
                </section>
              </div>

              <aside className="commercial-g21-side">
                <section className="commercial-card commercial-request360-card">
                  <div className="commercial-card-header">
                    <div className="commercial-card-title-only">Control Panel</div>
                  </div>
                  <label className="commercial-field">
                    <span>Status</span>
                    <select
                      value={status}
                      onChange={(event) => setStatus(event.target.value as ServiceRequestStatus)}
                    >
                      {controlStatuses.map((item) => (
                        <option key={item}>{item}</option>
                      ))}
                    </select>
                  </label>
                  <label className="commercial-field">
                    <span>Owner</span>
                    <input value={owner} onChange={(event) => setOwner(event.target.value)} />
                  </label>
                  <label className="commercial-field">
                    <span>Next action</span>
                    <input
                      value={nextAction}
                      onChange={(event) => setNextAction(event.target.value)}
                    />
                  </label>
                  <label className="commercial-field">
                    <span>Due date</span>
                    <input
                      type="date"
                      value={dueAt}
                      onChange={(event) => setDueAt(event.target.value)}
                    />
                  </label>
                  <button
                    type="button"
                    className="commercial-btn commercial-btn-primary commercial-btn-block"
                    disabled={saving}
                    onClick={saveControl}
                  >
                    {saving ? 'Saving...' : 'Save Update'}
                  </button>
                </section>

                <section className="commercial-card commercial-request360-card">
                  <div className="commercial-card-header">
                    <div className="commercial-card-title-only">Commercial Actions</div>
                  </div>
                  <button
                    type="button"
                    className="commercial-btn commercial-btn-block"
                    onClick={() => onPrepareQuotation(request.id)}
                  >
                    Prepare Quotation
                  </button>
                  <button
                    type="button"
                    className="commercial-btn commercial-btn-block"
                    disabled={saving}
                    onClick={scheduleAssessment}
                  >
                    Schedule Assessment
                  </button>
                  <button
                    type="button"
                    className="commercial-btn commercial-btn-block"
                    disabled={saving}
                    onClick={convertToOrder}
                  >
                    Convert to Service Order
                  </button>
                </section>
              </aside>
            </div>
          </div>

          <footer className="commercial-modal-footer">
            <button type="button" className="commercial-btn" onClick={onClose}>
              Close
            </button>
          </footer>
        </section>
      </div>

      {activityOpen ? (
        <div
          className="commercial-modal-backdrop commercial-modal-backdrop--nested"
          role="presentation"
          onMouseDown={() => setActivityOpen(false)}
        >
          <form
            className="commercial-modal"
            aria-label="Add Request Activity"
            onSubmit={saveActivity}
            onMouseDown={(event) => event.stopPropagation()}
          >
            <header className="commercial-modal-header">
              <h2>Add Request Activity</h2>
              <button
                type="button"
                className="commercial-modal-close"
                aria-label="Close"
                onClick={() => setActivityOpen(false)}
              >
                <IconX size={16} />
              </button>
            </header>
            <div className="commercial-modal-body">
              <div className="commercial-form-grid">
                <label className="commercial-field">
                  <span>Type</span>
                  <select
                    value={activityType}
                    onChange={(event) => setActivityType(event.target.value)}
                  >
                    {activityTypes.map((item) => (
                      <option key={item}>{item}</option>
                    ))}
                  </select>
                </label>
                <label className="commercial-field">
                  <span>Outcome</span>
                  <select
                    value={activityOutcome}
                    onChange={(event) => setActivityOutcome(event.target.value)}
                  >
                    {activityOutcomes.map((item) => (
                      <option key={item}>{item}</option>
                    ))}
                  </select>
                </label>
                <label className="commercial-field commercial-field--full">
                  <span>Detailed note</span>
                  <textarea
                    rows={4}
                    value={activityNote}
                    onChange={(event) => setActivityNote(event.target.value)}
                  />
                </label>
                <label className="commercial-field">
                  <span>Next action</span>
                  <input
                    value={activityNext}
                    onChange={(event) => setActivityNext(event.target.value)}
                  />
                </label>
                <label className="commercial-field">
                  <span>Next follow-up</span>
                  <input type="datetime-local" />
                </label>
              </div>
            </div>
            <footer className="commercial-modal-footer">
              <button
                type="button"
                className="commercial-btn"
                onClick={() => setActivityOpen(false)}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="commercial-btn commercial-btn-primary"
                disabled={saving}
              >
                Save Activity
              </button>
            </footer>
          </form>
        </div>
      ) : null}
    </>
  )
}
