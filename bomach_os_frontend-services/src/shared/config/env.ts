import { z } from 'zod'

const envSchema = z.object({
  VITE_API_BASE_URL: z.string().min(1).default('/api/v1'),
  VITE_NOTIFICATION_LIST_PATH: z.string().optional().default(''),
  VITE_NOTIFICATION_MARK_READ_PATH: z.string().optional().default(''),
  VITE_NOTIFICATION_MARK_ALL_READ_PATH: z.string().optional().default(''),
  VITE_ENABLE_MOCKS: z
    .enum(['true', 'false'])
    .default('true')
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
