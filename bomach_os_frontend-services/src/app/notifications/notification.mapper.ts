import type {
  AppNotification,
  NotificationListResult,
  NotificationStats,
  NotificationTone,
} from './notification.types'

export interface NotificationDto {
  id: number
  title: string
  message: string
  notification_type: string
  is_read: boolean
  link: string
  metadata: Record<string, unknown>
  created_at: string
}

export interface NotificationListDto {
  count?: number
  next?: string | null
  previous?: string | null
  results?: NotificationDto[]
  items?: NotificationDto[]
}

export interface NotificationStatsDto {
  unread_count: number
}

function tone(type: string): NotificationTone {
  switch (type) {
    case 'success':
      return 'success'
    case 'warning':
      return 'warning'
    case 'error':
      return 'danger'
    default:
      return 'info'
  }
}

export function mapNotification(dto: NotificationDto): AppNotification {
  return {
    id: String(dto.id),
    title: dto.title,
    description: dto.message,
    timestamp: dto.created_at,
    tone: tone(dto.notification_type),
    read: dto.is_read,
    ...(dto.link ? { link: dto.link } : {}),
    metadata: dto.metadata ?? {},
  }
}

export function mapNotificationList(dto: NotificationListDto): NotificationListResult {
  const rows = Array.isArray(dto.results) ? dto.results : Array.isArray(dto.items) ? dto.items : []

  return {
    count: typeof dto.count === 'number' ? dto.count : rows.length,
    next: dto.next ?? null,
    previous: dto.previous ?? null,
    notifications: rows.map(mapNotification),
  }
}

export function mapNotificationStats(dto: NotificationStatsDto): NotificationStats {
  return { unreadCount: dto.unread_count }
}
