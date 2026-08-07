import { apiClient } from '@/shared/api/api-client'
import { MOCK_API_PREFIX } from '@/mocks/mock-api'

import type {
  AddMilestoneInput,
  AddOrderUpdateInput,
  CreateDeliverableInput,
  DecideDeliverableInput,
  CreateExecutionTaskInput,
  CreateServiceOrderInput,
  FulfillmentWorkspace,
  UpdateExecutionTaskInput,
  UpdateServiceOrderInput,
} from '../types/fulfillment.types'

export const fulfillmentApi = {
  getWorkspace() {
    return apiClient.get<FulfillmentWorkspace>(`${MOCK_API_PREFIX}/fulfillment`)
  },

  createOrder(input: CreateServiceOrderInput) {
    return apiClient.post<FulfillmentWorkspace>(`${MOCK_API_PREFIX}/fulfillment/orders`, input)
  },

  updateOrder(orderId: string, input: UpdateServiceOrderInput) {
    return apiClient.patch<FulfillmentWorkspace>(
      `${MOCK_API_PREFIX}/fulfillment/orders/${orderId}`,
      input,
    )
  },

  advanceOrder(orderId: string) {
    return apiClient.post<FulfillmentWorkspace>(
      `${MOCK_API_PREFIX}/fulfillment/orders/${orderId}/advance`,
    )
  },

  addOrderUpdate(input: AddOrderUpdateInput) {
    return apiClient.post<FulfillmentWorkspace>(
      `${MOCK_API_PREFIX}/fulfillment/orders/${input.orderId}/activities`,
      input,
    )
  },

  addMilestone(input: AddMilestoneInput) {
    return apiClient.post<FulfillmentWorkspace>(
      `${MOCK_API_PREFIX}/fulfillment/orders/${input.orderId}/milestones`,
      input,
    )
  },

  createTask(input: CreateExecutionTaskInput) {
    return apiClient.post<FulfillmentWorkspace>(`${MOCK_API_PREFIX}/fulfillment/tasks`, input)
  },

  createDeliverable(input: CreateDeliverableInput) {
    return apiClient.post<FulfillmentWorkspace>(
      `${MOCK_API_PREFIX}/fulfillment/deliverables`,
      input,
    )
  },
  decideDeliverable(deliverableId: string, input: DecideDeliverableInput) {
    return apiClient.patch<FulfillmentWorkspace>(
      `${MOCK_API_PREFIX}/fulfillment/deliverables/${deliverableId}`,
      input,
    )
  },
  updateTask(taskId: string, input: UpdateExecutionTaskInput) {
    return apiClient.patch<FulfillmentWorkspace>(
      `${MOCK_API_PREFIX}/fulfillment/tasks/${taskId}`,
      input,
    )
  },
}
