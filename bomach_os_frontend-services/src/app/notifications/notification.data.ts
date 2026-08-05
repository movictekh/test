import type { AppNotification } from './notification.types'

export const mockNotifications: readonly AppNotification[] = [
  {
    id: 'notification-1',
    title: 'Quotation awaiting approval',
    description: 'QTN-260805-014 requires management review.',
    timestamp: '5 minutes ago',
    tone: 'warning',
    read: false,
  },
  {
    id: 'notification-2',
    title: 'Payment confirmed',
    description: 'INV-260805-009 received a mobilisation payment.',
    timestamp: '32 minutes ago',
    tone: 'success',
    read: false,
  },
  {
    id: 'notification-3',
    title: 'Request follow-up due',
    description: 'REQ-260804-031 needs a client follow-up today.',
    timestamp: '2 hours ago',
    tone: 'info',
    read: true,
  },
]
