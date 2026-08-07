import { formatCurrency } from '@/shared/lib/formatters'
import type { BrokerageProperty, Estate, EstatePlot } from '../types/specialized-services.types'
import { estateCounts } from '../workspaces/specialized-services.rules'

const cls = { Available: 'av', Reserved: 'rs', Sold: 'sd', Hold: 'hd' } as const

export function RealEstateInventoryScreen({
  estates,
  brokerage,
  selectedEstateId,
  selectedPlotNo,
  onSelectEstate,
  onSelectPlot,
  onSavePlot,
}: {
  estates: Estate[]
  brokerage: BrokerageProperty[]
  selectedEstateId: string
  selectedPlotNo: string | null
  onSelectEstate: (id: string) => void
  onSelectPlot: (no: string) => void
  onSavePlot: (plot: EstatePlot) => void
}) {
  const estate = estates.find((x) => x.id === selectedEstateId) ?? estates[0]
  if (!estate) return <main className="specialized-content">No estate configured.</main>
  const selected = estate.plots.find((x) => x.no === selectedPlotNo) ?? null
  const c = estateCounts(estate)
  return (
    <main className="specialized-content">
      <div className="specialized-filter-row">
        <select value={estate.id} onChange={(e) => onSelectEstate(e.target.value)}>
          {estates.map((x) => (
            <option key={x.id} value={x.id}>
              {x.name} — {x.location}
            </option>
          ))}
        </select>
      </div>
      <div className="specialized-kpi-grid">
        {[
          ['Total plots', c.total],
          ['Sold plots', c.sold],
          ['Reserved plots', c.reserved],
          ['Available plots', c.available],
        ].map(([l, v]) => (
          <article className="specialized-kpi-card" key={l}>
            <div>{l}</div>
            <strong>{v}</strong>
          </article>
        ))}
      </div>
      <div className="specialized-grid-2-1">
        <section className="specialized-card">
          <header className="specialized-card-header">
            <div>
              <div className="specialized-card-title">Estate Layout & Inventory</div>
              <div className="specialized-card-subtitle">
                Click a plot to reserve, sell, release or inspect it
              </div>
            </div>
            <div className="specialized-legend">
              <span>
                <i className="av" />
                Available
              </span>
              <span>
                <i className="rs" />
                Reserved
              </span>
              <span>
                <i className="sd" />
                Sold
              </span>
              <span>
                <i className="hd" />
                Hold
              </span>
            </div>
          </header>
          <div className="specialized-plot-grid">
            {estate.plots.map((p) => (
              <button
                key={p.no}
                type="button"
                className={`specialized-plot ${cls[p.status]}`}
                onClick={() => onSelectPlot(p.no)}
              >
                {p.no}
              </button>
            ))}
          </div>
        </section>
        <aside>
          <section className="specialized-card">
            <header className="specialized-card-header">
              <div className="specialized-card-title">Selected Plot</div>
            </header>
            {selected ? (
              <form
                key={`${estate.id}-${selected.no}-${selected.status}-${selected.client}-${selected.price}`}
                onSubmit={(e) => {
                  e.preventDefault()
                  const d = new FormData(e.currentTarget)
                  const status = d.get('status')
                  const client = d.get('client')
                  const price = d.get('price')
                  onSavePlot({
                    ...selected,
                    status: (typeof status === 'string'
                      ? status
                      : selected.status) as EstatePlot['status'],
                    client: typeof client === 'string' ? client : '',
                    price: Number(typeof price === 'string' ? price : selected.price),
                  })
                }}
              >
                <div className="specialized-selected-kpi">
                  <div>{estate.name}</div>
                  <strong>Plot {selected.no}</strong>
                  <span>
                    {selected.size} sqm · {formatCurrency(selected.price)}
                  </span>
                </div>
                <label className="specialized-field">
                  <span>Status</span>
                  <select name="status" defaultValue={selected.status}>
                    <option>Available</option>
                    <option>Reserved</option>
                    <option>Sold</option>
                    <option>Hold</option>
                  </select>
                </label>
                <label className="specialized-field">
                  <span>Client / reservation holder</span>
                  <input name="client" defaultValue={selected.client} />
                </label>
                <label className="specialized-field">
                  <span>Agreed price</span>
                  <input name="price" type="number" defaultValue={selected.price} />
                </label>
                <button className="specialized-btn specialized-btn-primary specialized-btn-block">
                  Save Plot Transaction
                </button>
              </form>
            ) : (
              <div className="specialized-empty">Select a plot</div>
            )}
          </section>
          <section className="specialized-card">
            <header className="specialized-card-header">
              <div className="specialized-card-title">Brokerage Listings</div>
            </header>
            {brokerage.map((p) => (
              <div className="specialized-row" key={p.id}>
                <div className="specialized-row-icon">⌂</div>
                <div className="specialized-row-main">
                  <div className="specialized-row-name">{p.title}</div>
                  <div className="specialized-row-sub">
                    {p.location} · {formatCurrency(p.price)}
                  </div>
                </div>
                <span className="specialized-pill">{p.status}</span>
              </div>
            ))}
          </section>
        </aside>
      </div>
    </main>
  )
}
