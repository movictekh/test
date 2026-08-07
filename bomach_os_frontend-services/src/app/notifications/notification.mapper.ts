import type { AppNotification, NotificationTone } from './notification.types'

function objectValue(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : null
}

function stringField(object: Record<string, unknown>, ...keys: string[]): string | undefined {
  for (const key of keys) {
    const value = object[key]
    if (typeof value === 'string' && value.trim()) return value
  }
  return undefined
}

function booleanField(object: Record<string, unknown>, ...keys: string[]): boolean | undefined {
  for (const key of keys) {
    const value = object[key]
    if (typeof value === 'boolean') return value
  }
  return undefined
}

function tone(value: string | undefined): NotificationTone {
  const normalized = value?.toLowerCase()
  if (normalized === 'success') return 'success'
  if (normalized === 'warning' || normalized === 'warn') return 'warning'
  if (normalized === 'danger' || normalized === 'error' || normalized === 'critical')
    return 'danger'
  return 'info'
}

function rows(payload: unknown): unknown[] {
  if (Array.isArray(payload)) return payload
  const object = objectValue(payload)
  if (!object) return []

  for (const key of ['results', 'notifications', 'data', 'items']) {
    if (Array.isArray(object[key])) return object[key] as unknown[]
  }

  return []
}

/**
 * Compatibility mapper only.
 *
 * Business notification creation and recipient logic remain backend-owned.
 * Replace the aliases below with the exact generated OpenAPI DTO once the
 * notification module contract is published.
 */
export function mapNotificationPayload(payload: unknown): AppNotification[] {
  return rows(payload).flatMap((row, index) => {
    const object = objectValue(row)
    if (!object) return []

    const id =
      stringField(object, 'id', 'uuid', 'notification_id') ?? `backend-notification-${index}`

    const title = stringField(object, 'title', 'subject', 'heading') ?? 'Service notification'

    const description = stringField(object, 'description', 'message', 'body', 'detail') ?? ''

    const timestamp = stringField(object, 'timestamp', 'created_at', 'createdAt', 'date') ?? ''

    const read = booleanField(object, 'read', 'is_read', 'isRead') ?? false

    const entityType = stringField(
      object,
      'entity_type',
      'entityType',
      'resource_type',
      'resourceType',
    )

    const entityId = stringField(
      object,
      'entity_id',
      'entityId',
      'resource_id',
      'resourceId',
      'reference_id',
    )

    return [
      {
        id,
        title,
        description,
        timestamp,
        tone: tone(stringField(object, 'tone', 'severity', 'level', 'type')),
        read,
        ...(entityType ? { entityType } : {}),
        ...(entityId ? { entityId } : {}),
      },
    ]
  })
}
