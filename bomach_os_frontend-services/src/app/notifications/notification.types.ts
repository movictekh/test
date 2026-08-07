export type NotificationTone = 'info' | 'success' | 'warning' | 'danger'

export interface AppNotification {
  id: string
  title: string
  description: string
  timestamp: string
  tone: NotificationTone
  read: boolean
  entityType?: string
  entityId?: string
}

export interface NotificationListResult {
  configured: boolean
  notifications: AppNotification[]
}
