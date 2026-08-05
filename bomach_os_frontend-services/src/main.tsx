import '@fontsource-variable/inter'
import '@/styles/index.css'

import { RouterProvider } from '@tanstack/react-router'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { AppProviders } from '@/app/providers/AppProviders'
import { router } from '@/app/router/router'
import { env } from '@/shared/config/env'

async function enableApiMocking(): Promise<void> {
  if (!import.meta.env.DEV || !env.enableMocks) {
    return
  }

  const { worker } = await import('@/mocks/browser')

  await worker.start({
    onUnhandledRequest: 'bypass',
    serviceWorker: {
      url: '/mockServiceWorker.js',
    },
  })
}

async function bootstrap(): Promise<void> {
  await enableApiMocking()

  const rootElement = document.getElementById('root')

  if (!rootElement) {
    throw new Error('The root application element was not found.')
  }

  createRoot(rootElement).render(
    <StrictMode>
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>
    </StrictMode>,
  )
}

void bootstrap()
