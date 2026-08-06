import { delay, http, HttpResponse } from 'msw'

import { env } from '@/shared/config/env'

import { getCommercialWorkspace } from './commercial.mock-db'

const endpoint = (path: string) => `${env.apiBaseUrl}${path}`

export const commercialHandlers = [
  http.get(endpoint('/ui-prototype/commercial'), async () => {
    await delay(180)
    return HttpResponse.json(getCommercialWorkspace())
  }),
]
