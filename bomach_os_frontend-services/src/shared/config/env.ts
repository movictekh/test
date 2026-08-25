import { z } from 'zod'

function getDefaultApiBaseUrl(): string {
  if (typeof window !== 'undefined') {
    const searchParams = new URLSearchParams(window.location.search)
    const override = searchParams.get('apiBaseUrl') || searchParams.get('backendUrl') || searchParams.get('apiUrl')
    if (override) {
      const clean = override.trim().replace(/\/+$/, '')
      return clean.endsWith('/api/v1') ? clean : `${clean}/api/v1`
    }

    const hostname = window.location.hostname.toLowerCase()
    const referrer = (document.referrer || '').toLowerCase()

    // 1. Test environments (bomach-os-test.web.app or localhost) -> test backend
    const isTestEnvironment =
      hostname.includes('bomach-os-test') ||
      hostname.includes('-test.web.app') ||
      referrer.includes('bomach-os-test') ||
      hostname === 'localhost' ||
      hostname === '127.0.0.1' ||
      hostname === '[::1]' ||
      hostname.endsWith('.local')

    if (isTestEnvironment) {
      return 'https://bomachauthtest.bgbot.app/api/v1'
    }

    // 2. Production app environments (bomach-os-app.web.app) -> production backend without test
    const isProdAppEnvironment =
      hostname.includes('bomach-os-app') ||
      referrer.includes('bomach-os-app') ||
      hostname === 'bomachauth.bgbot.app'

    if (isProdAppEnvironment) {
      return 'https://bomachauth.bgbot.app/api/v1'
    }
  }

  if (import.meta.env.DEV) {
    return 'https://bomachauthtest.bgbot.app/api/v1'
  }

  return 'https://bomachauth.bgbot.app/api/v1'
}



const envSchema = z.object({
  VITE_API_BASE_URL: z.string().min(1).default(getDefaultApiBaseUrl()),
  VITE_NOTIFICATION_LIST_PATH: z.string().optional().default(''),
  VITE_NOTIFICATION_MARK_READ_PATH: z.string().optional().default(''),
  VITE_NOTIFICATION_MARK_ALL_READ_PATH: z.string().optional().default(''),
  VITE_ENABLE_MOCKS: z
    .enum(['true', 'false'])
    .default('false')
    .transform((value) => value === 'true'),
})

const rawEnv: Record<string, unknown> = import.meta.env

const result = envSchema.safeParse({
  VITE_API_BASE_URL:
    typeof rawEnv.VITE_API_BASE_URL === 'string' ? rawEnv.VITE_API_BASE_URL : undefined,
  VITE_NOTIFICATION_LIST_PATH:
    typeof rawEnv.VITE_NOTIFICATION_LIST_PATH === 'string'
      ? rawEnv.VITE_NOTIFICATION_LIST_PATH
      : undefined,
  VITE_NOTIFICATION_MARK_READ_PATH:
    typeof rawEnv.VITE_NOTIFICATION_MARK_READ_PATH === 'string'
      ? rawEnv.VITE_NOTIFICATION_MARK_READ_PATH
      : undefined,
  VITE_NOTIFICATION_MARK_ALL_READ_PATH:
    typeof rawEnv.VITE_NOTIFICATION_MARK_ALL_READ_PATH === 'string'
      ? rawEnv.VITE_NOTIFICATION_MARK_ALL_READ_PATH
      : undefined,
  VITE_ENABLE_MOCKS:
    typeof rawEnv.VITE_ENABLE_MOCKS === 'string' ? rawEnv.VITE_ENABLE_MOCKS : undefined,
})

if (!result.success) {
  console.error('Invalid frontend environment configuration', result.error.flatten().fieldErrors)
  throw new Error('Invalid frontend environment configuration')
}

export const env = {
  apiBaseUrl: result.data.VITE_API_BASE_URL.replace(/\/$/, ''),
  enableMocks: result.data.VITE_ENABLE_MOCKS,
  notificationListPath: result.data.VITE_NOTIFICATION_LIST_PATH,
  notificationMarkReadPath: result.data.VITE_NOTIFICATION_MARK_READ_PATH,
  notificationMarkAllReadPath: result.data.VITE_NOTIFICATION_MARK_ALL_READ_PATH,
} as const
