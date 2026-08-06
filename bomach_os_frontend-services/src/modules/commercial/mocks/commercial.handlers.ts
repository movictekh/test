import { delay, http, HttpResponse } from 'msw'

import { env } from '@/shared/config/env'

import {
  createMockServiceRequest,
  getCommercialWorkspace,
  updateMockServiceRequest,
} from './commercial.mock-db'
import type { CreateServiceRequestInput, ServiceRequestStatus } from '../types/commercial.types'

const endpoint = (path: string) => `${env.apiBaseUrl}${path}`

export const commercialHandlers = [
  http.get(endpoint('/ui-prototype/commercial'), async () => {
    await delay(180)
    return HttpResponse.json(getCommercialWorkspace())
  }),

  http.post(endpoint('/ui-prototype/commercial/requests'), async ({ request }) => {
    await delay(260)
    const body = (await request.json()) as CreateServiceRequestInput
    if (
      !body.client ||
      !body.phone ||
      !body.service ||
      !body.branch ||
      !body.details ||
      !body.dueAt
    ) {
      return HttpResponse.json({ detail: 'Complete all required request fields.' }, { status: 422 })
    }
    return HttpResponse.json(createMockServiceRequest(body), { status: 201 })
  }),

  http.patch(
    endpoint('/ui-prototype/commercial/requests/:requestId'),
    async ({ params, request }) => {
      await delay(180)
      const body = (await request.json()) as {
        status?: ServiceRequestStatus
        owner?: string
        nextAction?: string
        dueAt?: string
        estimate?: number
        activity?: {
          at: string
          title: string
          actor: string
          description: string
        }
      }
      return HttpResponse.json(updateMockServiceRequest(String(params.requestId), body))
    },
  ),
]
