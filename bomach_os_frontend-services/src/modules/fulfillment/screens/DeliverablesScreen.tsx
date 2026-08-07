import type { Deliverable } from '../types/fulfillment.types'

export function DeliverablesScreen({
  deliverables,
  onCreate,
  onOpen,
}: {
  deliverables: Deliverable[]
  onCreate: () => void
  onOpen: (deliverable: Deliverable) => void
}) {
  return (
    <main className="fulfillment-content">
      <section className="fulfillment-card">
        <header className="fulfillment-card-header">
          <div>
            <div className="fulfillment-card-title">Deliverables & Document Inbox</div>
            <div className="fulfillment-card-subtitle">
              Reports, drawings, plans, certificates and client approvals
            </div>
          </div>
          <button
            type="button"
            className="fulfillment-btn fulfillment-btn-primary"
            onClick={onCreate}
          >
            Add Deliverable
          </button>
        </header>
        <div className="fulfillment-table-wrap">
          <table className="fulfillment-table fulfillment-deliverables-table">
            <thead>
              <tr>
                <th>Deliverable</th>
                <th>Order</th>
                <th>Type</th>
                <th>Version</th>
                <th>Owner</th>
                <th>Client Visible</th>
                <th>Date</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {deliverables.map((item) => (
                <tr key={item.id}>
                  <td>
                    <b>{item.title}</b>
                    <div className="fulfillment-row-sub">{item.id}</div>
                  </td>
                  <td>{item.orderId}</td>
                  <td>{item.type}</td>
                  <td>{item.version}</td>
                  <td>{item.owner}</td>
                  <td>{item.clientVisible ? 'Yes' : 'No'}</td>
                  <td>{item.date}</td>
                  <td>
                    <span className="fulfillment-pill fulfillment-pill-blue">{item.status}</span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="fulfillment-btn fulfillment-btn-small"
                      onClick={() => onOpen(item)}
                    >
                      Open
                    </button>
                  </td>
                </tr>
              ))}
              {deliverables.length === 0 ? (
                <tr>
                  <td colSpan={9}>
                    <div className="fulfillment-empty">No deliverables yet.</div>
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  )
}
