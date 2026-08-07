import { delay, http, HttpResponse } from 'msw'
import { MOCK_API_PREFIX } from '@/mocks/mock-api'
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
  http.get(endpoint(`${MOCK_API_PREFIX}/specialized-services`), async () => {
    await delay(160)
    return HttpResponse.json(getSpecializedWorkspace())
  }),
  http.post(endpoint(`${MOCK_API_PREFIX}/specialized-services/estates`), async ({ request }) => {
    await delay(180)
    const body = (await request.json()) as CreateEstateInput
    return HttpResponse.json(createMockEstate(body), { status: 201 })
  }),
  http.patch(
    endpoint(`${MOCK_API_PREFIX}/specialized-services/estates/:estateId/plots/:plotNo`),
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
  http.post(endpoint(`${MOCK_API_PREFIX}/specialized-services/brokerage`), async ({ request }) => {
    await delay(180)
    const body = (await request.json()) as CreateBrokeragePropertyInput
    return HttpResponse.json(createMockBrokerageProperty(body), { status: 201 })
  }),
]
