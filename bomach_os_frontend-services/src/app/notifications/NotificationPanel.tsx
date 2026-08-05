import { IconAlertTriangle, IconBell, IconCircleCheck, IconInfoCircle } from '@tabler/icons-react'
import { useMemo, useState } from 'react'

import { Button } from '@/shared/ui/button'
import { Drawer } from '@/shared/ui/drawer'
import { EmptyState } from '@/shared/ui/empty-state'

import { mockNotifications } from './notification.data'
import type { NotificationTone } from './notification.types'

const toneIcons = {
  info: IconInfoCircle,
  success: IconCircleCheck,
  warning: IconAlertTriangle,
  danger: IconAlertTriangle,
} as const

const toneClasses: Record<NotificationTone, string> = {
  info: 'bg-brand-50 text-brand-700',
  success: 'bg-success-50 text-success-700',
  warning: 'bg-warning-50 text-warning-700',
  danger: 'bg-danger-50 text-danger-700',
}

export function NotificationPanel() {
  const [open, setOpen] = useState(false)
  const [readIds, setReadIds] = useState<Set<string>>(
    () => new Set(mockNotifications.filter((item) => item.read).map((item) => item.id)),
  )

  const unreadCount = useMemo(
    () => mockNotifications.filter((item) => !readIds.has(item.id)).length,
    [readIds],
  )

  const markAllRead = () => {
    setReadIds(new Set(mockNotifications.map((item) => item.id)))
  }

  return (
    <>
      <Button
        variant="ghost"
        size="icon"
        className="relative text-white hover:bg-white/10 hover:text-white"
        aria-label={unreadCount > 0 ? `Notifications, ${unreadCount} unread` : 'Notifications'}
        onClick={() => setOpen(true)}
      >
        <IconBell size={19} />
        {unreadCount > 0 ? (
          <span className="bg-accent-600 absolute top-1.5 right-1.5 grid min-w-4 place-items-center rounded-full px-1 text-[0.5625rem] font-black text-white">
            {unreadCount}
          </span>
        ) : null}
      </Button>

      <Drawer
        open={open}
        title="Notifications"
        description="Important service activity that needs your attention."
        size="md"
        onClose={() => setOpen(false)}
        footer={
          unreadCount > 0 ? (
            <Button variant="outline" size="sm" onClick={markAllRead}>
              Mark all as read
            </Button>
          ) : null
        }
      >
        {mockNotifications.length === 0 ? (
          <EmptyState
            title="No notifications"
            description="Important activity and reminders will appear here."
          />
        ) : (
          <div className="space-y-2">
            {mockNotifications.map((notification) => {
              const read = readIds.has(notification.id)
              const Icon = toneIcons[notification.tone]

              return (
                <button
                  key={notification.id}
                  type="button"
                  className="border-border hover:bg-surface-muted rounded-control flex w-full items-start gap-3 border p-3 text-left transition-colors"
                  onClick={() => setReadIds((current) => new Set([...current, notification.id]))}
                >
                  <span
                    className={`grid size-9 shrink-0 place-items-center rounded-full ${toneClasses[notification.tone]}`}
                  >
                    <Icon size={18} aria-hidden="true" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-start justify-between gap-3">
                      <span className="text-foreground text-xs font-bold">
                        {notification.title}
                      </span>
                      {!read ? (
                        <span className="bg-accent-600 mt-1 size-2 shrink-0 rounded-full" />
                      ) : null}
                    </span>
                    <span className="text-foreground-muted mt-1 block text-xs leading-5">
                      {notification.description}
                    </span>
                    <span className="text-foreground-subtle mt-1.5 block text-[0.6875rem]">
                      {notification.timestamp}
                    </span>
                  </span>
                </button>
              )
            })}
          </div>
        )}
      </Drawer>
    </>
  )
}
