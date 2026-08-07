import { formatCurrency } from '@/shared/lib/formatters'
import type { CommercialServiceRequest } from '@/modules/commercial/types/commercial.types'
import type { ServiceOrder } from '@/modules/fulfillment/types/fulfillment.types'
import type {
  SpecializedProfileId,
  SpecializedServiceProfile,
} from '../types/specialized-services.types'

export function SpecializedServiceControlScreen({
  profiles,
  selectedId,
  requests,
  orders,
  onSelect,
  onOpenOrder,
}: {
  profiles: SpecializedServiceProfile[]
  selectedId: SpecializedProfileId
  requests: CommercialServiceRequest[]
  orders: ServiceOrder[]
  onSelect: (id: SpecializedProfileId) => void
  onOpenOrder: (id: string) => void
}) {
  const p = profiles.find((x) => x.id === selectedId) ?? profiles[0]
  if (!p) return null
  const rs = requests.filter((x) => x.division === p.division)
  const os = orders.filter((x) => x.division === p.division)
  const avg = os.length ? Math.round(os.reduce((a, b) => a + b.progress, 0) / os.length) : 0
  return (
    <main className="specialized-content">
      <div className="specialized-tabs">
        {profiles.map((x) => (
          <button
            key={x.id}
            type="button"
            className={`specialized-tab ${x.id === p.id ? 'on' : ''}`}
            onClick={() => onSelect(x.id)}
          >
            {x.label}
          </button>
        ))}
      </div>
      <div className="specialized-kpi-grid">
        {[
          ['Active requests', rs.length],
          ['Active orders', os.filter((x) => x.status !== 'Completed').length],
          ['Average completion', `${avg}%`],
          ['Order value', formatCurrency(os.reduce((a, b) => a + b.value, 0))],
        ].map(([l, v]) => (
          <article className="specialized-kpi-card" key={l}>
            <div>{l}</div>
            <strong>{v}</strong>
          </article>
        ))}
      </div>
      <section className="specialized-card">
        <header className="specialized-card-header">
          <div>
            <div className="specialized-card-title">{p.title}</div>
            <div className="specialized-card-subtitle">{p.description}</div>
          </div>
        </header>
        <div className="specialized-lifecycle">
          {p.stages.map((s, i) => (
            <article
              className={`specialized-step ${i < 3 ? 'done' : i === 3 ? 'active' : ''}`}
              key={s}
            >
              <small>{String(i + 1).padStart(2, '0')}</small>
              <b>{s}</b>
            </article>
          ))}
        </div>
      </section>
      <section className="specialized-card">
        <header className="specialized-card-header">
          <div className="specialized-card-title">Live Orders</div>
        </header>
        <div className="specialized-table-wrap">
          <table className="specialized-table">
            <thead>
              <tr>
                <th>Order</th>
                <th>Client</th>
                <th>Service</th>
                <th>Stage</th>
                <th>Progress</th>
                <th>Owner</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {os.map((o) => (
                <tr key={o.id}>
                  <td>
                    <b>{o.id}</b>
                  </td>
                  <td>{o.client}</td>
                  <td>{o.service}</td>
                  <td>{o.stage}</td>
                  <td>
                    <div className="specialized-progress">
                      <i style={{ width: `${o.progress}%` }} />
                    </div>
                  </td>
                  <td>{o.owner}</td>
                  <td>
                    <button
                      type="button"
                      className="specialized-btn specialized-btn-small"
                      onClick={() => onOpenOrder(o.id)}
                    >
                      Open
                    </button>
                  </td>
                </tr>
              ))}
              {!os.length ? (
                <tr>
                  <td colSpan={7}>No active orders.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  )
}
