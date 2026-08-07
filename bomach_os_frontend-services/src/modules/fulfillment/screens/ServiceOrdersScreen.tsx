import { useMemo, useState } from 'react'

import type { ServiceOrder } from '../types/fulfillment.types'
import { orderBoardColumns } from '../workspaces/fulfillment-workflow.rules'

export function ServiceOrdersScreen({
  orders,
  onOpenOrder,
}: {
  orders: ServiceOrder[]
  onOpenOrder: (order: ServiceOrder) => void
}) {
  const [search, setSearch] = useState('')
  const needle = search.trim().toLowerCase()

  const visible = useMemo(
    () =>
      orders.filter((order) =>
        !needle
          ? true
          : `${order.id} ${order.client} ${order.service}`.toLowerCase().includes(needle),
      ),
    [needle, orders],
  )

  return (
    <main className="fulfillment-content">
      <div className="fulfillment-filter-row">
        <input
          aria-label="Search orders"
          placeholder="Search orders..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </div>

      <div className="fulfillment-kanban" id="orderBoard">
        {orderBoardColumns.map((column) => {
          const columnOrders = visible.filter((order) => order.status === column)

          return (
            <section className="fulfillment-column" key={column}>
              <div className="fulfillment-column-header">
                <span>{column}</span>
                <span>{columnOrders.length}</span>
              </div>

              {columnOrders.length > 0 ? (
                columnOrders.map((order) => (
                  <button
                    type="button"
                    key={order.id}
                    className="fulfillment-task-card fulfillment-order-card"
                    onClick={() => onOpenOrder(order)}
                  >
                    <b>{order.client}</b>
                    <small>
                      {order.service} · {order.id}
                    </small>
                    <div className="fulfillment-progress">
                      <i style={{ width: `${order.progress}%` }} />
                    </div>
                    <div className="fulfillment-task-footer">
                      <span className="fulfillment-pill fulfillment-pill-blue">
                        {order.progress}%
                      </span>
                      <span className="fulfillment-row-sub">{order.dueAt}</span>
                    </div>
                  </button>
                ))
              ) : (
                <div className="fulfillment-empty fulfillment-empty-column">No orders</div>
              )}
            </section>
          )
        })}
      </div>
    </main>
  )
}
