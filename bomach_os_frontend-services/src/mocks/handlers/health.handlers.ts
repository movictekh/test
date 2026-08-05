import { delay, http, HttpResponse } from 'msw'

export const healthHandlers = [
  http.get('/api/health', async () => {
    await delay(250)

    return HttpResponse.json({
      data: {
        status: 'ok',
        service: 'Bomach Service Operations Frontend Mock API',
        timestamp: new Date().toISOString(),
      },
      message: 'Mock API is ready.',
    })
  }),
]
