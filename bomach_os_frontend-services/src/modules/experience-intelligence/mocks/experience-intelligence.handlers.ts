import { delay, http, HttpResponse } from 'msw'

import { getFulfillmentWorkspace } from '@/modules/fulfillment/mocks/fulfillment.mock-db'
import { env } from '@/shared/config/env'

import type {
  CreateFeedbackInput,
  UpdateFeedbackInput,
} from '../types/experience-intelligence.types'
import {
  createMockFeedback,
  getExperienceIntelligenceWorkspace,
  updateMockFeedback,
} from './experience-intelligence.mock-db'

const endpoint = (path: string) => `${env.apiBaseUrl}${path}`

export const experienceIntelligenceHandlers = [
  http.get(endpoint('/ui-prototype/experience-intelligence'), async () => {
    await delay(120)
    return HttpResponse.json(getExperienceIntelligenceWorkspace())
  }),

  http.post(endpoint('/ui-prototype/experience-intelligence/feedback'), async ({ request }) => {
    await delay(180)

    const body = (await request.json()) as CreateFeedbackInput
    const order = getFulfillmentWorkspace().orders.find(
      (candidate) => candidate.id === body.orderId,
    )

    if (!order) {
      return HttpResponse.json({ detail: 'Select a valid Service Order.' }, { status: 422 })
    }

    if (!body.comment.trim()) {
      return HttpResponse.json({ detail: 'Enter the client comment.' }, { status: 422 })
    }

    return HttpResponse.json(createMockFeedback(body, order), { status: 201 })
  }),

  http.patch(
    endpoint('/ui-prototype/experience-intelligence/feedback/:feedbackId'),
    async ({ params, request }) => {
      await delay(160)
      const body = (await request.json()) as UpdateFeedbackInput

      return HttpResponse.json(updateMockFeedback(String(params.feedbackId), body))
    },
  ),
]
