import '@fontsource-variable/inter'
import '@/styles/index.css'

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { AppProviders } from '@/app/providers/AppProviders'
import { ApplicationRouter } from '@/app/router/ApplicationRouter'
import { env } from '@/shared/config/env'

const MOCK_WORKER_URL = '/mockServiceWorker.js'

/**
 * MSW hangs/reloads when a mock worker is registered but not controlling the page.
 * Unregister those stale workers so `worker.start()` can do a clean register.
 */
async function clearStaleMockWorkers(): Promise<void> {
  if (!('serviceWorker' in navigator)) return

  const absoluteWorkerUrl = new URL(MOCK_WORKER_URL, window.location.href).href
  const registrations = await navigator.serviceWorker.getRegistrations()

  await Promise.all(
    registrations.map(async (registration) => {
      const scripts = [registration.active, registration.waiting, registration.installing]
        .filter((worker): worker is ServiceWorker => worker != null)
        .map((worker) => worker.scriptURL)

      const isMockWorker = scripts.some((scriptUrl) => scriptUrl === absoluteWorkerUrl)
      if (!isMockWorker) return

      if (!navigator.serviceWorker.controller) {
        await registration.unregister()
      }
    }),
  )
}

async function enableApiMocking(): Promise<void> {
  if (!import.meta.env.DEV || !env.enableMocks) {
    return
  }

  if (!window.isSecureContext || !('serviceWorker' in navigator)) {
    console.warn(
      'API mocks need http://localhost:5173 (secure context). Network IPs over HTTP cannot register the mock service worker.',
    )
    return
  }

  await clearStaleMockWorkers()

  const { worker } = await import('@/mocks/browser')

  try {
    await Promise.race([
      worker.start({
        onUnhandledRequest: 'bypass',
        quiet: true,
        serviceWorker: {
          url: MOCK_WORKER_URL,
        },
      }),
      new Promise<never>((_, reject) => {
        window.setTimeout(() => {
          reject(new Error('Mock service worker start timed out'))
        }, 5000)
      }),
    ])
  } catch (error) {
    await clearStaleMockWorkers()
    console.warn('API mocking could not start. Continuing without MSW.', error)
  }
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
        <ApplicationRouter />
      </AppProviders>
    </StrictMode>,
  )
}

void bootstrap().catch((error) => {
  console.error('Application bootstrap failed', error)
  const rootElement = document.getElementById('root')
  if (rootElement) {
    rootElement.innerHTML =
      '<main style="padding:24px;font:14px/1.5 system-ui,sans-serif"><h1>App failed to start</h1><p>Check the browser console for details, then hard-refresh.</p></main>'
  }
})
