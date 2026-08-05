export type NotificationTone = 'info' | 'success' | 'warning' | 'danger'

export interface AppNotification {
  id: string
  title: string
  description: string
  timestamp: string
  tone: NotificationTone
  read: boolean
}
