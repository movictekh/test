import { delay, http, HttpResponse } from 'msw'

import { env } from '@/shared/config/env'

import { dashboardActivityMock, dashboardSummaryMock } from './dashboard.mock-data'

function endpoint(path: string): string {
  return `${env.apiBaseUrl}${path}`
}

export const dashboardHandlers = [
  http.get(endpoint('/sop/dashboard/summary/:userId'), async () => {
    await delay(260)
    return HttpResponse.json(dashboardSummaryMock)
  }),

  http.get(endpoint('/sop/dashboard/recent-activity'), async () => {
    await delay(180)
    return HttpResponse.json(dashboardActivityMock)
  }),
]
