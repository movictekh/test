import { apiClient } from '@/shared/api/api-client'
import { env } from '@/shared/config/env'

import { mapNotificationPayload } from './notification.mapper'
import type { NotificationListResult } from './notification.types'

function configuredPath(path: string): string | null {
  const trimmed = path.trim()
  return trimmed ? trimmed : null
}

export const notificationApi = {
  async list(): Promise<NotificationListResult> {
    const path = configuredPath(env.notificationListPath)
    if (!path) return { configured: false, notifications: [] }

    const payload = await apiClient.get<unknown>(path)
    return {
      configured: true,
      notifications: mapNotificationPayload(payload),
    }
  },

  async markRead(notificationId: string): Promise<void> {
    const template = configuredPath(env.notificationMarkReadPath)
    if (!template) return

    const path = template.replace('{id}', encodeURIComponent(notificationId))
    await apiClient.patch<unknown>(path, { read: true })
  },

  async markAllRead(): Promise<void> {
    const path = configuredPath(env.notificationMarkAllReadPath)
    if (!path) return

    await apiClient.patch<unknown>(path, { read: true })
  },
}
