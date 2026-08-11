import { apiClient } from '@/shared/api/api-client'

import {
  mapEmployeeOptions,
  mapServiceOrder,
  mapServiceOrderActivity,
  mapServiceOrderList,
  mapServiceOrderMilestone,
} from './service-order.mapper'
import type {
  AddOrderActivityInput,
  AddOrderMilestoneInput,
  CreateServiceOrderFromInvoiceInput,
  ServiceOrderFilters,
  UpdateServiceOrderInput,
} from './service-order.types'

function orderQuery(filters: ServiceOrderFilters = {}) {
  const query = new URLSearchParams()
  const limit = filters.limit ?? 10
  const page = filters.page ?? 1
  query.set('limit', String(limit))
  query.set('offset', String((page - 1) * limit))
  if (filters.search) query.set('search', filters.search)
  if (filters.orderStatus) query.set('order_status', filters.orderStatus)
  if (filters.paymentStatus) query.set('payment_status', filters.paymentStatus)
  if (filters.invoiceId) query.set('invoice_id', String(filters.invoiceId))
  return query.toString()
}

export const serviceOrderApi = {
  async list(filters: ServiceOrderFilters = {}) {
    return mapServiceOrderList(await apiClient.get<unknown>(`/orders?${orderQuery(filters)}`))
  },

  async detail(orderId: number) {
    return mapServiceOrder(await apiClient.get<unknown>(`/orders/${orderId}`))
  },

  async employees() {
    return mapEmployeeOptions(
      await apiClient.get<unknown>('/employees/employees?is_active=true&limit=100&offset=0'),
    )
  },

  async createFromInvoice(input: CreateServiceOrderFromInvoiceInput) {
    return mapServiceOrder(
      await apiClient.post<unknown>(`/invoices/${input.invoiceId}/service-order`, {
        ...(input.assignedToId ? { assigned_to_id: input.assignedToId } : {}),
        ...(input.dueDate ? { due_date: input.dueDate } : {}),
        description: input.description ?? '',
        next_action: input.nextAction,
      }),
    )
  },

  async update(orderId: number, input: UpdateServiceOrderInput) {
    return mapServiceOrder(
      await apiClient.patch<unknown>(`/orders/${orderId}`, {
        ...(input.assignedToId !== undefined ? { assigned_to_id: input.assignedToId } : {}),
        ...(input.dueDate !== undefined ? { due_date: input.dueDate } : {}),
        ...(input.description !== undefined ? { description: input.description } : {}),
        ...(input.nextAction !== undefined ? { next_action: input.nextAction } : {}),
      }),
    )
  },

  async addActivity(orderId: number, input: AddOrderActivityInput) {
    return mapServiceOrderActivity(
      await apiClient.post<unknown>(`/orders/${orderId}/activities`, {
        activity_type: input.activityType,
        visibility: input.visibility,
        note: input.note,
        ...(input.nextAction ? { next_action: input.nextAction } : {}),
      }),
    )
  },

  async addMilestone(orderId: number, input: AddOrderMilestoneInput) {
    return mapServiceOrderMilestone(
      await apiClient.post<unknown>(`/orders/${orderId}/milestones`, {
        name: input.name,
        status: 'pending',
        sort_order: input.sortOrder,
        client_visible: input.clientVisible ?? true,
        ...(input.dueDate ? { due_date: input.dueDate } : {}),
      }),
    )
  },

  async completeMilestone(orderId: number, milestoneId: number) {
    return mapServiceOrder(
      await apiClient.post<unknown>(`/orders/${orderId}/milestones/${milestoneId}/complete`, {}),
    )
  },
}
