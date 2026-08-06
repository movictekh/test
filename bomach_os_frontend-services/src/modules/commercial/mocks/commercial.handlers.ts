import { delay, http, HttpResponse } from 'msw'

import { env } from '@/shared/config/env'

import { createMockServiceRequest, getCommercialWorkspace } from './commercial.mock-db'
import type { CreateServiceRequestInput } from '../types/commercial.types'

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
]
