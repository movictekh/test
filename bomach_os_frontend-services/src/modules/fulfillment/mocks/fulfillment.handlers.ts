import { delay, http, HttpResponse } from 'msw'
import { MOCK_API_PREFIX } from '@/mocks/mock-api'

import { env } from '@/shared/config/env'

import type {
  AddMilestoneInput,
  AddOrderUpdateInput,
  CreateDeliverableInput,
  DecideDeliverableInput,
  CreateExecutionTaskInput,
  CreateServiceOrderInput,
  UpdateExecutionTaskInput,
  UpdateServiceOrderInput,
} from '../types/fulfillment.types'
import {
  addMockMilestone,
  addMockOrderUpdate,
  advanceMockOrder,
  createMockDeliverable,
  createMockOrder,
  createMockTask,
  decideMockDeliverable,
  getFulfillmentWorkspace,
  updateMockOrder,
  updateMockTask,
} from './fulfillment.mock-db'

const endpoint = (path: string) => `${env.apiBaseUrl}${path}`

export const fulfillmentHandlers = [
  http.get(endpoint(`${MOCK_API_PREFIX}/fulfillment`), async () => {
    await delay(160)
    return HttpResponse.json(getFulfillmentWorkspace())
  }),

  http.post(endpoint(`${MOCK_API_PREFIX}/fulfillment/orders`), async ({ request }) => {
    await delay(240)
    const body = (await request.json()) as CreateServiceOrderInput

    if (
      !body.client ||
      !body.service ||
      !body.owner ||
      !body.dueAt ||
      !body.mode ||
      Number(body.value) <= 0
    ) {
      return HttpResponse.json(
        { detail: 'Complete the service order fields before creating the order.' },
        { status: 422 },
      )
    }

    return HttpResponse.json(createMockOrder(body), { status: 201 })
  }),

  http.patch(
    endpoint(`${MOCK_API_PREFIX}/fulfillment/orders/:orderId`),
    async ({ params, request }) => {
      await delay(180)
      const body = (await request.json()) as UpdateServiceOrderInput
      return HttpResponse.json(updateMockOrder(String(params.orderId), body))
    },
  ),

  http.post(
    endpoint(`${MOCK_API_PREFIX}/fulfillment/orders/:orderId/advance`),
    async ({ params }) => {
      await delay(180)
      return HttpResponse.json(advanceMockOrder(String(params.orderId)))
    },
  ),

  http.post(
    endpoint(`${MOCK_API_PREFIX}/fulfillment/orders/:orderId/activities`),
    async ({ params, request }) => {
      await delay(180)
      const body = (await request.json()) as AddOrderUpdateInput
      return HttpResponse.json(
        addMockOrderUpdate({
          ...body,
          orderId: String(params.orderId),
        }),
      )
    },
  ),

  http.post(
    endpoint(`${MOCK_API_PREFIX}/fulfillment/orders/:orderId/milestones`),
    async ({ params, request }) => {
      await delay(160)
      const body = (await request.json()) as AddMilestoneInput
      return HttpResponse.json(
        addMockMilestone({
          ...body,
          orderId: String(params.orderId),
        }),
      )
    },
  ),

  http.post(endpoint(`${MOCK_API_PREFIX}/fulfillment/deliverables`), async ({ request }) => {
    await delay(180)
    const body = (await request.json()) as CreateDeliverableInput
    if (!body.orderId || !body.title || !body.version)
      return HttpResponse.json(
        { detail: 'Complete the deliverable order, title and version.' },
        { status: 422 },
      )
    return HttpResponse.json(createMockDeliverable(body), { status: 201 })
  }),
  http.patch(
    endpoint(`${MOCK_API_PREFIX}/fulfillment/deliverables/:deliverableId`),
    async ({ params, request }) => {
      await delay(150)
      const body = (await request.json()) as DecideDeliverableInput
      return HttpResponse.json(decideMockDeliverable(String(params.deliverableId), body))
    },
  ),

  http.post(endpoint(`${MOCK_API_PREFIX}/fulfillment/tasks`), async ({ request }) => {
    await delay(220)
    const body = (await request.json()) as CreateExecutionTaskInput

    if (!body.title || !body.orderId || !body.owner || !body.dueAt) {
      return HttpResponse.json(
        { detail: 'Complete the execution task fields before creating the task.' },
        { status: 422 },
      )
    }

    return HttpResponse.json(createMockTask(body), { status: 201 })
  }),

  http.patch(
    endpoint(`${MOCK_API_PREFIX}/fulfillment/tasks/:taskId`),
    async ({ params, request }) => {
      await delay(150)
      const body = (await request.json()) as UpdateExecutionTaskInput
      return HttpResponse.json(updateMockTask(String(params.taskId), body))
    },
  ),
]
