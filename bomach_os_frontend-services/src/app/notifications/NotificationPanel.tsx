import { IconAlertTriangle, IconBell, IconCircleCheck, IconInfoCircle } from '@tabler/icons-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useState } from 'react'

import { getRecordDestination } from '@/shared/navigation'
import { Button } from '@/shared/ui/button'
import { Drawer } from '@/shared/ui/drawer'
import { EmptyState } from '@/shared/ui/empty-state'

import { notificationApi } from './notification.api'
import { notificationKeys, notificationQueries } from './notification.queries'
import type { AppNotification, NotificationTone } from './notification.types'

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
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const query = useQuery(notificationQueries.list())

  const markRead = useMutation({
    mutationFn: (notificationId: string) => notificationApi.markRead(notificationId),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: notificationKeys.list(),
      }),
  })

  const markAllRead = useMutation({
    mutationFn: () => notificationApi.markAllRead(),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: notificationKeys.list(),
      }),
  })

  const notifications = query.data?.notifications ?? []
  const unreadCount = notifications.filter((item) => !item.read).length

  const openNotification = async (notification: AppNotification) => {
    if (!notification.read) {
      await markRead.mutateAsync(notification.id)
    }

    const destination = getRecordDestination(notification.entityType, notification.entityId)

    if (destination) {
      setOpen(false)
      await navigate({
        to: '/app/$section',
        params: { section: destination.section },
        search: destination.search,
      })
    }
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
          unreadCount > 0 && query.data?.configured ? (
            <Button
              variant="outline"
              size="sm"
              disabled={markAllRead.isPending}
              onClick={() => markAllRead.mutate()}
            >
              Mark all as read
            </Button>
          ) : null
        }
      >
        {query.isPending ? (
          <div className="space-y-2" aria-label="Loading notifications">
            {[1, 2, 3].map((item) => (
              <div
                key={item}
                className="border-border bg-surface-muted rounded-control h-20 animate-pulse border"
              />
            ))}
          </div>
        ) : query.isError ? (
          <EmptyState
            title="Notifications unavailable"
            description="The notification service could not be reached. Try again."
            action={
              <Button variant="outline" size="sm" onClick={() => void query.refetch()}>
                Retry
              </Button>
            }
          />
        ) : !query.data?.configured ? (
          <EmptyState
            title="Notification API awaiting backend contract"
            description="The frontend notification UI is ready. Configure the backend list/read endpoints when the notification module contract is published."
          />
        ) : notifications.length === 0 ? (
          <EmptyState
            title="No notifications"
            description="Important backend-generated activity will appear here."
          />
        ) : (
          <div className="space-y-2">
            {notifications.map((notification) => {
              const Icon = toneIcons[notification.tone]

              return (
                <button
                  key={notification.id}
                  type="button"
                  className="border-border hover:bg-surface-muted rounded-control flex w-full items-start gap-3 border p-3 text-left transition-colors"
                  onClick={() => void openNotification(notification)}
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
                      {!notification.read ? (
                        <span className="bg-accent-600 mt-1 size-2 shrink-0 rounded-full" />
                      ) : null}
                    </span>
                    <span className="text-foreground-muted mt-1 block text-xs leading-5">
                      {notification.description}
                    </span>
                    {notification.timestamp ? (
                      <span className="text-foreground-subtle mt-1.5 block text-[0.6875rem]">
                        {notification.timestamp}
                      </span>
                    ) : null}
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
