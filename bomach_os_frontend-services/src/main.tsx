import '@fontsource-variable/inter'
import '@/styles/index.css'

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { AppProviders } from '@/app/providers/AppProviders'
import { ApplicationRouter } from '@/app/router/ApplicationRouter'
import { env } from '@/shared/config/env'

const MOCK_WORKER_URL = `${import.meta.env.BASE_URL}mockServiceWorker.js`
const MOCK_START_TIMEOUT_MS = 8000

function renderBootstrapFailure(error: unknown): void {
  console.error('Application bootstrap failed', error)

  const rootElement = document.getElementById('root')
  if (!rootElement) return

  const message = error instanceof Error ? error.message : 'Unknown application startup error'

  rootElement.innerHTML = `
    <main style="max-width:720px;margin:64px auto;padding:24px;font:14px/1.6 Inter,system-ui,sans-serif">
      <h1 style="margin:0 0 12px;font-size:22px">Development app could not start</h1>
      <p style="margin:0 0 12px">
        ${message.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')}
      </p>
      <p style="margin:0">
        If this is an MSW startup error, use <strong>http://localhost:5173</strong>.
        After switching from the old startup code, unregister any old mock worker
        once in DevTools → Application → Service Workers, then reload.
      </p>
    </main>
  `
}

async function startApiMocking(): Promise<void> {
  if (!import.meta.env.DEV || !env.enableMocks) return

  if (!window.isSecureContext) {
    throw new Error(
      'API mocking requires a secure browser context. Use http://localhost:5173 instead of a LAN IP over HTTP.',
    )
  }

  if (!('serviceWorker' in navigator)) {
    throw new Error('This browser does not support Service Workers required by MSW.')
  }

  const { worker } = await import('@/mocks/browser')

  let timeoutId: number | undefined

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
        timeoutId = window.setTimeout(() => {
          reject(
            new Error(
              'MSW did not finish starting within 8 seconds. The app was not mounted because development API mocks are required.',
            ),
          )
        }, MOCK_START_TIMEOUT_MS)
      }),
    ])
  } finally {
    if (timeoutId !== undefined) {
      window.clearTimeout(timeoutId)
    }
  }
}

async function bootstrap(): Promise<void> {
  const rootElement = document.getElementById('root')

  if (!rootElement) {
    throw new Error('The root application element was not found.')
  }

  await startApiMocking()

  createRoot(rootElement).render(
    <StrictMode>
      <AppProviders>
        <ApplicationRouter />
      </AppProviders>
    </StrictMode>,
  )
}

void bootstrap().catch(renderBootstrapFailure)
