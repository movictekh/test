import { apiClient } from '@/shared/api/api-client'

import type {
  AddMilestoneInput,
  AddOrderUpdateInput,
  CreateExecutionTaskInput,
  CreateServiceOrderInput,
  FulfillmentWorkspace,
  UpdateExecutionTaskInput,
  UpdateServiceOrderInput,
} from '../types/fulfillment.types'

export const fulfillmentApi = {
  getWorkspace() {
    return apiClient.get<FulfillmentWorkspace>('/ui-prototype/fulfillment')
  },

  createOrder(input: CreateServiceOrderInput) {
    return apiClient.post<FulfillmentWorkspace>('/ui-prototype/fulfillment/orders', input)
  },

  updateOrder(orderId: string, input: UpdateServiceOrderInput) {
    return apiClient.patch<FulfillmentWorkspace>(
      `/ui-prototype/fulfillment/orders/${orderId}`,
      input,
    )
  },

  advanceOrder(orderId: string) {
    return apiClient.post<FulfillmentWorkspace>(
      `/ui-prototype/fulfillment/orders/${orderId}/advance`,
    )
  },

  addOrderUpdate(input: AddOrderUpdateInput) {
    return apiClient.post<FulfillmentWorkspace>(
      `/ui-prototype/fulfillment/orders/${input.orderId}/activities`,
      input,
    )
  },

  addMilestone(input: AddMilestoneInput) {
    return apiClient.post<FulfillmentWorkspace>(
      `/ui-prototype/fulfillment/orders/${input.orderId}/milestones`,
      input,
    )
  },

  createTask(input: CreateExecutionTaskInput) {
    return apiClient.post<FulfillmentWorkspace>('/ui-prototype/fulfillment/tasks', input)
  },

  updateTask(taskId: string, input: UpdateExecutionTaskInput) {
    return apiClient.patch<FulfillmentWorkspace>(`/ui-prototype/fulfillment/tasks/${taskId}`, input)
  },
}
