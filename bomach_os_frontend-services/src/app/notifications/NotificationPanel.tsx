import { IconAlertTriangle, IconBell, IconCircleCheck, IconInfoCircle } from '@tabler/icons-react'
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useState } from 'react'

import { useAuth } from '@/app/auth'
import { hasPermission, PERMISSIONS } from '@/app/permissions'
import { ApiError } from '@/shared/api/api-error'
import { getRecordDestination } from '@/shared/navigation'
import { Button } from '@/shared/ui/button'
import { Drawer } from '@/shared/ui/drawer'
import { EmptyState } from '@/shared/ui/empty-state'
import { useToast } from '@/shared/ui'

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

function metadataString(metadata: Record<string, unknown>, key: string): string | undefined {
  const value = metadata[key]
  if (typeof value === 'string' && value.trim()) return value
  if (typeof value === 'number') return String(value)
  return undefined
}

function parseBackendLink(link: string | undefined) {
  if (!link) return null

  const match = link.match(
    /^\/(orders|quotes|invoices|approvals|requests|tasks|deliverables|feedback)\/(.+)$/,
  )
  if (!match) return null

  const [, type, id] = match
  if (!type || !id) return null

  const entityType =
    type === 'quotes'
      ? 'quote'
      : type === 'invoices'
        ? 'invoice'
        : type === 'approvals'
          ? 'approval'
          : type === 'requests'
            ? 'request'
            : type === 'orders'
              ? 'order'
              : type.slice(0, -1)

  return getRecordDestination(entityType, id)
}

function notificationErrorCopy(error: unknown): { title: string; description: string } {
  if (error instanceof ApiError) {
    if (error.status === 0) {
      return {
        title: 'Notifications unavailable',
        description: 'The notification service could not be reached right now.',
      }
    }

    if (error.status === 404) {
      return {
        title: 'Notifications not configured',
        description: 'This environment does not currently expose the notification endpoint.',
      }
    }

    if (error.status >= 500) {
      return {
        title: 'Notifications unavailable',
        description: 'The notification service returned a server error. Please try again shortly.',
      }
    }
  }

  return {
    title: 'Notifications unavailable',
    description: 'Notifications could not be loaded right now.',
  }
}

export function NotificationPanel() {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()
  const { user } = useAuth()

  const canList = hasPermission(user, PERMISSIONS.notificationsList)
  const canView = hasPermission(user, PERMISSIONS.notificationsView)
  const canMarkRead = hasPermission(user, PERMISSIONS.notificationsMarkRead)
  const canMarkAllRead = hasPermission(user, PERMISSIONS.notificationsMarkAllRead)

  const listQuery = useInfiniteQuery({
    ...notificationQueries.list(),
    enabled: canList,
  })
  const statsQuery = useQuery({
    ...notificationQueries.stats(),
    enabled: canView,
  })

  const markRead = useMutation({
    mutationFn: (notificationId: string) => notificationApi.markRead(notificationId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: notificationKeys.all })
    },
    onError: () => {
      toast.error('Notification could not be marked as read')
    },
  })

  const markAllRead = useMutation({
    mutationFn: () => notificationApi.markAllRead(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: notificationKeys.all })
    },
    onError: () => {
      toast.error('Notifications could not be marked as read')
    },
  })

  if (!canList && !canView) return null

  const notifications = listQuery.data?.pages.flatMap((page) => page.notifications) ?? []
  const unreadCount = statsQuery.data?.unreadCount ?? 0
  const listErrorCopy = notificationErrorCopy(listQuery.error)

  const openNotification = async (notification: AppNotification) => {
    if (!notification.read && canMarkRead) {
      try {
        await markRead.mutateAsync(notification.id)
      } catch {
        // A read-state failure should not block the notification destination.
      }
    }

    const destination =
      getRecordDestination(
        metadataString(notification.metadata, 'entity_type'),
        metadataString(notification.metadata, 'entity_id'),
      ) ?? parseBackendLink(notification.link)

    if (!destination) return

    setOpen(false)
    await navigate({
      to: '/app/$section',
      params: { section: destination.section },
      search: destination.search,
    })
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
            {unreadCount > 99 ? '99+' : unreadCount}
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
          unreadCount > 0 && canMarkAllRead ? (
            <Button
              variant="outline"
              size="sm"
              disabled={markAllRead.isPending}
              onClick={() => markAllRead.mutate()}
            >
              {markAllRead.isPending ? 'Marking...' : 'Mark all as read'}
            </Button>
          ) : null
        }
      >
        {listQuery.isPending && canList ? (
          <div className="space-y-2" aria-label="Loading notifications">
            {[1, 2, 3].map((item) => (
              <div
                key={item}
                className="border-border bg-surface-muted rounded-control h-20 animate-pulse border"
              />
            ))}
          </div>
        ) : listQuery.isError ? (
          <EmptyState
            title={listErrorCopy.title}
            description={listErrorCopy.description}
            action={
              <Button variant="outline" size="sm" onClick={() => void listQuery.refetch()}>
                Retry
              </Button>
            }
          />
        ) : !canList ? (
          <EmptyState
            title="Notification list unavailable"
            description="Your role can see notification status but cannot list notifications."
          />
        ) : notifications.length === 0 ? (
          <EmptyState
            title="All caught up"
            description="No new notifications right now. New approvals, tasks, and service updates will appear here."
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
                  disabled={markRead.isPending}
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
                    <span className="text-foreground-subtle mt-1.5 block text-[0.6875rem]">
                      {new Date(notification.timestamp).toLocaleString('en-NG')}
                    </span>
                  </span>
                </button>
              )
            })}
          </div>
        )}

        {canList && listQuery.hasNextPage ? (
          <div className="mt-3 flex justify-center">
            <Button
              variant="outline"
              size="sm"
              disabled={listQuery.isFetchingNextPage}
              onClick={() => void listQuery.fetchNextPage()}
            >
              {listQuery.isFetchingNextPage ? 'Loading...' : 'Load more'}
            </Button>
          </div>
        ) : null}
      </Drawer>
    </>
  )
}
