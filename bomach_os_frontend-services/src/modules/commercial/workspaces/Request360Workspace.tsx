import { IconX } from '@tabler/icons-react'
import type { CommercialServiceRequest } from '../types/commercial.types'
const money = new Intl.NumberFormat('en-NG', {
  style: 'currency',
  currency: 'NGN',
  maximumFractionDigits: 0,
})
export function Request360Workspace({
  request,
  onClose,
}: {
  request: CommercialServiceRequest
  onClose: () => void
}) {
  return (
    <div className="commercial-drawer-backdrop" onMouseDown={onClose}>
      <aside
        className="commercial-drawer"
        aria-label={`Request 360 ${request.id}`}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <header className="commercial-drawer-header">
          <div>
            <span>Request 360</span>
            <h2>{request.id}</h2>
            <p>
              {request.client} · {request.service}
            </p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close">
            <IconX size={17} />
          </button>
        </header>
        <div className="commercial-drawer-body">
          <div className="commercial-detail-hero">
            {[
              ['Status', request.status],
              ['Priority', request.priority],
              ['Owner', request.owner],
              ['Value', money.format(request.estimate || request.budget)],
            ].map(([a, b]) => (
              <div key={a}>
                <small>{a}</small>
                <b>{b}</b>
              </div>
            ))}
          </div>
          <section className="commercial-detail-card">
            <h3>Client and request summary</h3>
            <dl>
              {[
                ['Client', request.client],
                ['Phone', request.phone],
                ['Email', request.email || '—'],
                ['Branch', request.branch],
                ['Division', request.division],
                ['Required date', request.dueAt],
              ].map(([a, b]) => (
                <div key={a}>
                  <dt>{a}</dt>
                  <dd>{b}</dd>
                </div>
              ))}
            </dl>
          </section>
          <section className="commercial-detail-card">
            <h3>Scope and intake</h3>
            <p>{request.details}</p>
            <dl>
              {Object.entries(request.intakeResponses).map(([a, b]) => (
                <div key={a}>
                  <dt>{a}</dt>
                  <dd>{b || '—'}</dd>
                </div>
              ))}
            </dl>
          </section>
          <section className="commercial-detail-card">
            <h3>Next action</h3>
            <p>{request.nextAction}</p>
          </section>
          <section className="commercial-detail-card">
            <h3>Activity</h3>
            <div className="commercial-timeline">
              {request.activities.length ? (
                request.activities.map((x) => (
                  <article key={x.id}>
                    <i />
                    <div>
                      <b>{x.title}</b>
                      <small>
                        {x.actor} · {new Date(x.at).toLocaleString('en-NG')}
                      </small>
                      <p>{x.description}</p>
                    </div>
                  </article>
                ))
              ) : (
                <p>No activity recorded.</p>
              )}
            </div>
          </section>
        </div>
      </aside>
    </div>
  )
}
