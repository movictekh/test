import { delay, http, HttpResponse } from 'msw'
import { env } from '@/shared/config/env'
import type {
  CreateBrokeragePropertyInput,
  CreateEstateInput,
  UpdatePlotInput,
} from '../types/specialized-services.types'
import {
  createMockBrokerageProperty,
  createMockEstate,
  getSpecializedWorkspace,
  updateMockPlot,
} from './specialized-services.mock-db'
const endpoint = (path: string) => `${env.apiBaseUrl}${path}`
export const specializedServicesHandlers = [
  http.get(endpoint('/ui-prototype/specialized-services'), async () => {
    await delay(160)
    return HttpResponse.json(getSpecializedWorkspace())
  }),
  http.post(endpoint('/ui-prototype/specialized-services/estates'), async ({ request }) => {
    await delay(180)
    const body = (await request.json()) as CreateEstateInput
    return HttpResponse.json(createMockEstate(body), { status: 201 })
  }),
  http.patch(
    endpoint('/ui-prototype/specialized-services/estates/:estateId/plots/:plotNo'),
    async ({ params, request }) => {
      await delay(150)
      const body = (await request.json()) as UpdatePlotInput
      return HttpResponse.json(
        updateMockPlot({
          ...body,
          estateId: String(params.estateId),
          plotNo: String(params.plotNo),
        }),
      )
    },
  ),
  http.post(endpoint('/ui-prototype/specialized-services/brokerage'), async ({ request }) => {
    await delay(180)
    const body = (await request.json()) as CreateBrokeragePropertyInput
    return HttpResponse.json(createMockBrokerageProperty(body), { status: 201 })
  }),
]
