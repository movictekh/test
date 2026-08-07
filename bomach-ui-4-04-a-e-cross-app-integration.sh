#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ! -f package.json ]] || ! grep -q '"name": "bomach_os_frontend-services"' package.json; then
  echo "Error: run this from bomach_os_frontend-services."
  exit 1
fi

python3 <<'PY'
from pathlib import Path
import re

def read(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"Missing required file: {path}")
    return p.read_text()

def write(path: str, content: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)

def replace_once(path: str, old: str, new: str, *, required=True) -> None:
    text = read(path)
    if old not in text:
        if required:
            raise SystemExit(f"Could not find expected block in {path}")
        return
    write(path, text.replace(old, new, 1))

def add_import_once(path: str, anchor: str, line: str) -> None:
    text = read(path)
    if line.strip() in text:
        return
    if anchor not in text:
        raise SystemExit(f"Import anchor not found in {path}: {anchor}")
    write(path, text.replace(anchor, anchor + line, 1))

def insert_before_last_return_in_function(path: str, function_name: str, return_text: str, snippet: str) -> None:
    text = read(path)
    marker = f"export function {function_name}"
    start = text.find(marker)
    if start == -1:
        raise SystemExit(f"{function_name} not found in {path}")

    next_export = text.find("\nexport function ", start + len(marker))
    end = next_export if next_export != -1 else len(text)
    block = text[start:end]
    if snippet.strip() in block:
        return

    idx = block.rfind(return_text)
    if idx == -1:
        raise SystemExit(f"Return marker not found for {function_name} in {path}")

    block = block[:idx] + snippet + "\n  " + block[idx:]
    write(path, text[:start] + block + text[end:])

# ---------------------------------------------------------------------------
# A. INTERNAL RECORD LINKING
# ---------------------------------------------------------------------------
write(
    "src/shared/navigation/record-links.ts",
    """export interface AppRecordSearch {
  request?: string
  quotation?: string
  invoice?: string
  approval?: string
  order?: string
  task?: string
  deliverable?: string
  feedback?: string
}

export type RecordEntityType =
  | 'request'
  | 'quotation'
  | 'invoice'
  | 'approval'
  | 'order'
  | 'task'
  | 'deliverable'
  | 'feedback'

export interface RecordDestination {
  section:
    | 'service-requests'
    | 'quotations'
    | 'invoices-payments'
    | 'approvals'
    | 'service-orders'
    | 'execution-tasks'
    | 'deliverables'
    | 'feedback-quality'
  search: AppRecordSearch
}

export function getRecordDestination(
  entityType: string | undefined,
  entityId: string | undefined,
): RecordDestination | null {
  if (!entityType || !entityId) return null

  switch (entityType.toLowerCase()) {
    case 'request':
      return { section: 'service-requests', search: { request: entityId } }
    case 'quotation':
    case 'quote':
      return { section: 'quotations', search: { quotation: entityId } }
    case 'invoice':
    case 'payment':
      return { section: 'invoices-payments', search: { invoice: entityId } }
    case 'approval':
      return { section: 'approvals', search: { approval: entityId } }
    case 'order':
      return { section: 'service-orders', search: { order: entityId } }
    case 'task':
      return { section: 'execution-tasks', search: { task: entityId } }
    case 'deliverable':
    case 'document':
      return { section: 'deliverables', search: { deliverable: entityId } }
    case 'feedback':
      return { section: 'feedback-quality', search: { feedback: entityId } }
    default:
      return null
  }
}
""",
)

write(
    "src/shared/navigation/RecordLink.tsx",
    """import { Link } from '@tanstack/react-router'
import type { PropsWithChildren } from 'react'

import { cn } from '@/shared/lib/cn'

import { getRecordDestination } from './record-links'

export function RecordLink({
  entityType,
  entityId,
  children,
  className,
}: PropsWithChildren<{
  entityType: string
  entityId: string
  className?: string
}>) {
  const destination = getRecordDestination(entityType, entityId)

  if (!destination) return <>{children}</>

  return (
    <Link
      to="/app/$section"
      params={{ section: destination.section }}
      search={destination.search}
      className={cn('font-semibold text-brand-700 hover:underline', className)}
      onClick={(event) => event.stopPropagation()}
    >
      {children}
    </Link>
  )
}
""",
)

write(
    "src/shared/navigation/index.ts",
    """export { RecordLink } from './RecordLink'
export { getRecordDestination } from './record-links'
export { useDeepLinkedSelection } from './useDeepLinkedSelection'
export type {
  AppRecordSearch,
  RecordDestination,
  RecordEntityType,
} from './record-links'
""",
)

write(
    "src/shared/navigation/useDeepLinkedSelection.ts",
    """import { useState } from 'react'

/**
 * Merge URL deep-link ids with local selection without syncing via useEffect.
 * Closing dismisses the current deep-link until the URL param changes.
 */
export function useDeepLinkedSelection(deepLinkId: string | undefined) {
  const [manualId, setManualId] = useState<string | null>(null)
  const [dismissedDeepLink, setDismissedDeepLink] = useState<string | null>(null)

  const selectedId =
    manualId ?? (deepLinkId && deepLinkId !== dismissedDeepLink ? deepLinkId : null)

  const select = (id: string | null) => {
    if (id === null) {
      if (deepLinkId && selectedId === deepLinkId) {
        setDismissedDeepLink(deepLinkId)
      }
      setManualId(null)
      return
    }

    setDismissedDeepLink(null)
    setManualId(id)
  }

  return [selectedId, select] as const
}
""",
)

# Route owns deep-link search state.
route_path = "src/routes/app/$section.tsx"
text = read(route_path)

if "type AppRecordSearch" not in text:
    text = text.replace(
        "import { PERMISSIONS, requireRoutePermission } from '@/app/permissions'\n",
        "import { PERMISSIONS, requireRoutePermission } from '@/app/permissions'\n"
        "import type { AppRecordSearch } from '@/shared/navigation'\n",
        1,
    )

if "function parseRecordSearch" not in text:
    anchor = "function formatSectionTitle(section: string): string {"
    idx = text.find(anchor)
    if idx == -1:
        raise SystemExit("Route title formatter not found.")
    parser = """function parseRecordSearch(search: Record<string, unknown>): AppRecordSearch {
  const stringValue = (value: unknown): string | undefined =>
    typeof value === 'string' && value.trim() ? value : undefined

  const result: AppRecordSearch = {}
  const request = stringValue(search.request)
  const quotation = stringValue(search.quotation)
  const invoice = stringValue(search.invoice)
  const approval = stringValue(search.approval)
  const order = stringValue(search.order)
  const task = stringValue(search.task)
  const deliverable = stringValue(search.deliverable)
  const feedback = stringValue(search.feedback)

  if (request) result.request = request
  if (quotation) result.quotation = quotation
  if (invoice) result.invoice = invoice
  if (approval) result.approval = approval
  if (order) result.order = order
  if (task) result.task = task
  if (deliverable) result.deliverable = deliverable
  if (feedback) result.feedback = feedback

  return result
}

"""
    text = text[:idx] + parser + text[idx:]

if "validateSearch: parseRecordSearch," not in text:
    text = text.replace(
        "export const Route = createFileRoute('/app/$section')({\n",
        "export const Route = createFileRoute('/app/$section')({\n  validateSearch: parseRecordSearch,\n",
        1,
    )

if "const recordSearch = Route.useSearch()" not in text:
    text = text.replace(
        "  const { section } = Route.useParams()\n",
        "  const { section } = Route.useParams()\n  const recordSearch = Route.useSearch()\n",
        1,
    )

text = text.replace(
    "return <CommercialSectionPage section={section as CommercialSection} />",
    "return <CommercialSectionPage section={section as CommercialSection} recordSearch={recordSearch} />",
)
text = text.replace(
    "return <FulfillmentSectionPage section={section as FulfillmentSection} />",
    "return <FulfillmentSectionPage section={section as FulfillmentSection} recordSearch={recordSearch} />",
)
text = text.replace(
    "return <ExperienceIntelligenceSectionPage section={section as ExperienceIntelligenceSection} />",
    "return (\n      <ExperienceIntelligenceSectionPage\n        section={section as ExperienceIntelligenceSection}\n        recordSearch={recordSearch}\n      />\n    )",
)
write(route_path, text)

# Commercial deep links.
commercial_page = "src/modules/commercial/pages/CommercialSectionPage.tsx"
text = read(commercial_page)
if "useDeepLinkedSelection" not in text:
    text = text.replace(
        "import { useMemo, useState } from 'react'",
        "import { useMemo, useState } from 'react'",
    )
    text = text.replace(
        "import type { AppRecordSearch } from '@/shared/navigation'\n",
        "import { useDeepLinkedSelection, type AppRecordSearch } from '@/shared/navigation'\n",
        1,
    )
    text = text.replace(
        "import { useEffect, useMemo, useState } from 'react'",
        "import { useMemo, useState } from 'react'",
    )

text = text.replace(
    "export function CommercialSectionPage({ section }: { section: CommercialSection }) {",
    """export function CommercialSectionPage({
  section,
  recordSearch,
}: {
  section: CommercialSection
  recordSearch?: AppRecordSearch
}) {""",
)

# Prefer deep-link hook over effect sync.
text = text.replace(
    "  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null)\n",
    "  const [selectedRequestId, setSelectedRequestId] = useDeepLinkedSelection(recordSearch?.request)\n",
)
text = text.replace(
    "  const [selectedQuotationId, setSelectedQuotationId] = useState<string | null>(null)\n",
    "  const [selectedQuotationId, setSelectedQuotationId] = useDeepLinkedSelection(\n    recordSearch?.quotation,\n  )\n",
)
text = text.replace(
    "  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null)\n",
    "  const [selectedInvoiceId, setSelectedInvoiceId] = useDeepLinkedSelection(recordSearch?.invoice)\n",
)
text = text.replace(
    "  const [selectedApprovalId, setSelectedApprovalId] = useState<string | null>(null)\n",
    "  const [selectedApprovalId, setSelectedApprovalId] = useDeepLinkedSelection(recordSearch?.approval)\n",
)

# Strip any leftover deep-link effect.
text = re.sub(
    r"\n  useEffect\(\(\) => \{\n    if \(recordSearch\?\.request\) setSelectedRequestId\(recordSearch\.request\)\n    if \(recordSearch\?\.quotation\) setSelectedQuotationId\(recordSearch\.quotation\)\n    if \(recordSearch\?\.invoice\) setSelectedInvoiceId\(recordSearch\.invoice\)\n    if \(recordSearch\?\.approval\) setSelectedApprovalId\(recordSearch\.approval\)\n  \}, \[\n    recordSearch\?\.request,\n    recordSearch\?\.quotation,\n    recordSearch\?\.invoice,\n    recordSearch\?\.approval,\n  \]\)\n",
    "\n",
    text,
    count=1,
)
if "useEffect" not in text:
    text = text.replace("import { useEffect, useMemo, useState } from 'react'", "import { useMemo, useState } from 'react'")
    text = text.replace("import { useMemo, useEffect, useState } from 'react'", "import { useMemo, useState } from 'react'")

write(commercial_page, text)

# Fulfillment deep links.
fulfillment_page = "src/modules/fulfillment/pages/FulfillmentSectionPage.tsx"
text = read(fulfillment_page)
text = text.replace(
    "import { useEffect, useMemo, useState } from 'react'",
    "import { useMemo, useState } from 'react'",
)
if "AppRecordSearch" not in text:
    text = text.replace(
        "import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'\n",
        "import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'\n"
        "import { useDeepLinkedSelection, type AppRecordSearch } from '@/shared/navigation'\n",
        1,
    )
else:
    text = text.replace(
        "import type { AppRecordSearch } from '@/shared/navigation'\n",
        "import { useDeepLinkedSelection, type AppRecordSearch } from '@/shared/navigation'\n",
        1,
    )
text = text.replace(
    "export function FulfillmentSectionPage({ section }: { section: FulfillmentSection }) {",
    """export function FulfillmentSectionPage({
  section,
  recordSearch,
}: {
  section: FulfillmentSection
  recordSearch?: AppRecordSearch
}) {""",
)
text = text.replace(
    "  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null)\n",
    "  const [selectedOrderId, setSelectedOrderId] = useDeepLinkedSelection(recordSearch?.order)\n",
)
text = text.replace(
    "  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)\n",
    "  const [selectedTaskId, setSelectedTaskId] = useDeepLinkedSelection(recordSearch?.task)\n",
)
text = text.replace(
    "  const [selectedDeliverableId, setSelectedDeliverableId] = useState<string | null>(null)\n",
    "  const [selectedDeliverableId, setSelectedDeliverableId] = useDeepLinkedSelection(\n    recordSearch?.deliverable,\n  )\n",
)
text = re.sub(
    r"\n  useEffect\(\(\) => \{\n    if \(recordSearch\?\.order\) setSelectedOrderId\(recordSearch\.order\)\n    if \(recordSearch\?\.task\) setSelectedTaskId\(recordSearch\.task\)\n    if \(recordSearch\?\.deliverable\) setSelectedDeliverableId\(recordSearch\.deliverable\)\n  \}, \[recordSearch\?\.order, recordSearch\?\.task, recordSearch\?\.deliverable\]\)\n",
    "\n",
    text,
    count=1,
)
write(fulfillment_page, text)

# Feedback deep links.
experience_page = "src/modules/experience-intelligence/pages/ExperienceIntelligenceSectionPage.tsx"
text = read(experience_page)
text = text.replace(
    "import { useEffect, useMemo, useState } from 'react'",
    "import { useMemo, useState } from 'react'",
)
if "useDeepLinkedSelection" not in text:
    text = text.replace(
        "import type { AppRecordSearch } from '@/shared/navigation'\n",
        "import { useDeepLinkedSelection, type AppRecordSearch } from '@/shared/navigation'\n",
        1,
    )
    if "AppRecordSearch" not in text:
        text = text.replace(
            "import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'\n",
            "import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'\n"
            "import { useDeepLinkedSelection, type AppRecordSearch } from '@/shared/navigation'\n",
            1,
        )
text = text.replace(
    """export function ExperienceIntelligenceSectionPage({
  section,
}: {
  section: ExperienceIntelligenceSection
}) {""",
    """export function ExperienceIntelligenceSectionPage({
  section,
  recordSearch,
}: {
  section: ExperienceIntelligenceSection
  recordSearch?: AppRecordSearch
}) {""",
)
text = text.replace(
    "  const [selectedFeedbackId, setSelectedFeedbackId] = useState<string | null>(null)\n",
    "  const [selectedFeedbackId, setSelectedFeedbackId] = useDeepLinkedSelection(recordSearch?.feedback)\n",
)
text = re.sub(
    r"\n  useEffect\(\(\) => \{\n    if \(recordSearch\?\.feedback\) setSelectedFeedbackId\(recordSearch\.feedback\)\n  \}, \[recordSearch\?\.feedback\]\)\n",
    "\n",
    text,
    count=1,
)
write(experience_page, text)

# Literal table columns remain unchanged; IDs become navigable.
feedback_screen = "src/modules/experience-intelligence/screens/FeedbackQualityScreen.tsx"
text = read(feedback_screen)
if "RecordLink" not in text:
    text = "import { RecordLink } from '@/shared/navigation'\n" + text
text = text.replace(
    "<td>{item.orderId}</td>",
    '<td><RecordLink entityType="order" entityId={item.orderId}>{item.orderId}</RecordLink></td>',
)
write(feedback_screen, text)

deliverables_screen = "src/modules/fulfillment/screens/DeliverablesScreen.tsx"
text = read(deliverables_screen)
if "RecordLink" not in text:
    text = "import { RecordLink } from '@/shared/navigation'\n\n" + text
text = text.replace(
    "<td>{item.orderId}</td>",
    '<td><RecordLink entityType="order" entityId={item.orderId}>{item.orderId}</RecordLink></td>',
)
write(deliverables_screen, text)

audit_screen = "src/modules/experience-intelligence/screens/AuditLogScreen.tsx"
text = read(audit_screen)
if "RecordLink" not in text:
    text = "import { RecordLink } from '@/shared/navigation'\n" + text
text = text.replace(
    "<td>{item.action}</td>",
    """<td>
                    {item.entityType && item.entityId ? (
                      <RecordLink entityType={item.entityType} entityId={item.entityId}>
                        {item.action}
                      </RecordLink>
                    ) : (
                      item.action
                    )}
                  </td>""",
)
write(audit_screen, text)

# ---------------------------------------------------------------------------
# B. BACKEND-OWNED NOTIFICATION API ADAPTER (NO LOCAL GENERATION)
# ---------------------------------------------------------------------------
env_path = "src/shared/config/env.ts"
text = read(env_path)
if "VITE_NOTIFICATION_LIST_PATH" not in text:
    text = text.replace(
        "  VITE_ENABLE_MOCKS: z\n",
        "  VITE_NOTIFICATION_LIST_PATH: z.string().optional().default(''),\n"
        "  VITE_NOTIFICATION_MARK_READ_PATH: z.string().optional().default(''),\n"
        "  VITE_NOTIFICATION_MARK_ALL_READ_PATH: z.string().optional().default(''),\n"
        "  VITE_ENABLE_MOCKS: z\n",
        1,
    )
    text = text.replace(
        "  VITE_ENABLE_MOCKS:\n",
        "  VITE_NOTIFICATION_LIST_PATH:\n"
        "    typeof rawEnv.VITE_NOTIFICATION_LIST_PATH === 'string'\n"
        "      ? rawEnv.VITE_NOTIFICATION_LIST_PATH\n"
        "      : undefined,\n"
        "  VITE_NOTIFICATION_MARK_READ_PATH:\n"
        "    typeof rawEnv.VITE_NOTIFICATION_MARK_READ_PATH === 'string'\n"
        "      ? rawEnv.VITE_NOTIFICATION_MARK_READ_PATH\n"
        "      : undefined,\n"
        "  VITE_NOTIFICATION_MARK_ALL_READ_PATH:\n"
        "    typeof rawEnv.VITE_NOTIFICATION_MARK_ALL_READ_PATH === 'string'\n"
        "      ? rawEnv.VITE_NOTIFICATION_MARK_ALL_READ_PATH\n"
        "      : undefined,\n"
        "  VITE_ENABLE_MOCKS:\n",
        1,
    )
    text = text.replace(
        "  enableMocks: result.data.VITE_ENABLE_MOCKS,\n",
        "  enableMocks: result.data.VITE_ENABLE_MOCKS,\n"
        "  notificationListPath: result.data.VITE_NOTIFICATION_LIST_PATH,\n"
        "  notificationMarkReadPath: result.data.VITE_NOTIFICATION_MARK_READ_PATH,\n"
        "  notificationMarkAllReadPath: result.data.VITE_NOTIFICATION_MARK_ALL_READ_PATH,\n",
        1,
    )
write(env_path, text)

# Extend types without assuming backend business rules.
write(
    "src/app/notifications/notification.types.ts",
    """export type NotificationTone = 'info' | 'success' | 'warning' | 'danger'

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
""",
)

write(
    "src/app/notifications/notification.mapper.ts",
    """import type { AppNotification, NotificationTone } from './notification.types'

function objectValue(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : null
}

function stringField(
  object: Record<string, unknown>,
  ...keys: string[]
): string | undefined {
  for (const key of keys) {
    const value = object[key]
    if (typeof value === 'string' && value.trim()) return value
  }
  return undefined
}

function booleanField(
  object: Record<string, unknown>,
  ...keys: string[]
): boolean | undefined {
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
  if (normalized === 'danger' || normalized === 'error' || normalized === 'critical') return 'danger'
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
      stringField(object, 'id', 'uuid', 'notification_id') ??
      `backend-notification-${index}`

    const title =
      stringField(object, 'title', 'subject', 'heading') ??
      'Service notification'

    const description =
      stringField(object, 'description', 'message', 'body', 'detail') ??
      ''

    const timestamp =
      stringField(object, 'timestamp', 'created_at', 'createdAt', 'date') ??
      ''

    const read =
      booleanField(object, 'read', 'is_read', 'isRead') ??
      false

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
""",
)

write(
    "src/app/notifications/notification.api.ts",
    """import { apiClient } from '@/shared/api/api-client'
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
""",
)

write(
    "src/app/notifications/notification.queries.ts",
    """import { queryOptions } from '@tanstack/react-query'

import { notificationApi } from './notification.api'

export const notificationKeys = {
  all: ['notifications'] as const,
  list: () => [...notificationKeys.all, 'list'] as const,
}

export const notificationQueries = {
  list: () =>
    queryOptions({
      queryKey: notificationKeys.list(),
      queryFn: () => notificationApi.list(),
      staleTime: 30_000,
      refetchInterval: 60_000,
      retry: 1,
    }),
}
""",
)

write(
    "src/app/notifications/NotificationPanel.tsx",
    """import {
  IconAlertTriangle,
  IconBell,
  IconCircleCheck,
  IconInfoCircle,
} from '@tabler/icons-react'
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

    const destination = getRecordDestination(
      notification.entityType,
      notification.entityId,
    )

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
        aria-label={
          unreadCount > 0
            ? `Notifications, ${unreadCount} unread`
            : 'Notifications'
        }
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
                className="border-border bg-surface-muted h-20 animate-pulse rounded-control border"
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
""",
)

write(
    "src/app/notifications/index.ts",
    """export { NotificationPanel } from './NotificationPanel'
export type {
  AppNotification,
  NotificationListResult,
  NotificationTone,
} from './notification.types'
""",
)

data_file = Path("src/app/notifications/notification.data.ts")
if data_file.exists():
    data_file.unlink()

# ---------------------------------------------------------------------------
# C. SHARED AUDIT STORE + FULL MOCK-DOMAIN INSTRUMENTATION
# ---------------------------------------------------------------------------
write(
    "src/shared/audit/mock-audit-store.ts",
    """export interface MockAuditEvent {
  id: string
  occurredAt: string
  actor: string
  area: string
  action: string
  entityType?: string
  entityId?: string
}

export interface AppendMockAuditEventInput {
  actor?: string
  area: string
  action: string
  entityType?: string
  entityId?: string
}

const auditEvents: MockAuditEvent[] = [
  {
    id: 'AUD-001',
    occurredAt: '2026-07-13 15:22',
    actor: 'Civil Engineer',
    area: 'Request',
    action: 'Updated REQ-260713-001 to Site Assessment',
    entityType: 'request',
    entityId: 'REQ-260713-001',
  },
  {
    id: 'AUD-002',
    occurredAt: '2026-07-13 14:50',
    actor: 'Legal Officer',
    area: 'Deliverable',
    action: 'Uploaded Deed of Assignment Draft for ORD-260713-004',
    entityType: 'order',
    entityId: 'ORD-260713-004',
  },
  {
    id: 'AUD-003',
    occurredAt: '2026-07-13 13:40',
    actor: 'Site Engineer',
    area: 'Milestone',
    action: 'Requested reinforcement inspection for ORD-260630-011',
    entityType: 'order',
    entityId: 'ORD-260630-011',
  },
  {
    id: 'AUD-004',
    occurredAt: '2026-07-13 12:25',
    actor: 'Property Manager',
    area: 'Plot',
    action: 'Reserved Fortress City plot 39',
    entityType: 'plot',
    entityId: 'EST-01-39',
  },
  {
    id: 'AUD-005',
    occurredAt: '2026-07-13 11:05',
    actor: 'Finance Officer',
    area: 'Payment',
    action: 'Confirmed ₦4,500,000 payment for INV-260713-004',
    entityType: 'invoice',
    entityId: 'INV-260713-004',
  },
]

function nowDisplay(): string {
  return new Date().toLocaleString('en-GB')
}

export function getMockAuditEvents(): MockAuditEvent[] {
  return auditEvents
}

export function appendMockAuditEvent(input: AppendMockAuditEventInput): void {
  auditEvents.unshift({
    id: `AUD-${Date.now().toString().slice(-7)}`,
    occurredAt: nowDisplay(),
    actor: input.actor ?? 'Service Operations User',
    area: input.area,
    action: input.action,
    ...(input.entityType ? { entityType: input.entityType } : {}),
    ...(input.entityId ? { entityId: input.entityId } : {}),
  })
}
""",
)

# Rewrite experience DB onto the shared audit store.
write(
    "src/modules/experience-intelligence/mocks/experience-intelligence.mock-db.ts",
    """import {
  appendMockAuditEvent,
  getMockAuditEvents,
} from '@/shared/audit/mock-audit-store'

import type {
  CreateFeedbackInput,
  ExperienceIntelligenceWorkspace,
  ServiceFeedback,
  UpdateFeedbackInput,
} from '../types/experience-intelligence.types'

const feedback: ServiceFeedback[] = [
  {
    id: 'FDB-001',
    orderId: 'ORD-260712-033',
    client: 'Benji Vendor Network',
    service: 'Express Delivery',
    rating: 5,
    type: 'Completion',
    comment: 'Fast delivery and good communication.',
    status: 'Closed',
    date: '2026-07-12',
    correctiveAction: '',
  },
  {
    id: 'FDB-002',
    orderId: 'ORD-260701-019',
    client: 'Greenview Cooperative',
    service: 'Cadastral Land Survey',
    rating: 4,
    type: 'Milestone',
    comment: 'Work is good, but more frequent updates would help.',
    status: 'Open',
    date: '2026-07-10',
    correctiveAction: 'Survey team to send a progress update after each field milestone.',
    followUpAt: '2026-07-15',
  },
  {
    id: 'FDB-003',
    orderId: 'ORD-260630-011',
    client: 'Noble Homes Ltd',
    service: 'Building Construction',
    rating: 4,
    type: 'Milestone',
    comment: 'Site team is professional. Keep us informed before material requests.',
    status: 'Action Required',
    date: '2026-07-11',
    correctiveAction: 'Project Manager to give 48-hour notice before material calls.',
    followUpAt: '2026-07-14',
  },
]

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

export function getExperienceIntelligenceWorkspace(): ExperienceIntelligenceWorkspace {
  return {
    feedback,
    audit: getMockAuditEvents(),
  }
}

export function createMockFeedback(
  input: CreateFeedbackInput,
  order: { id: string; client: string; service: string } | undefined,
): ExperienceIntelligenceWorkspace {
  if (!order) return getExperienceIntelligenceWorkspace()

  const id = `FDB-${Date.now().toString().slice(-5)}`

  feedback.unshift({
    id,
    orderId: order.id,
    client: order.client,
    service: order.service,
    rating: input.rating,
    type: input.type,
    comment: input.comment,
    status: input.status,
    date: today(),
    correctiveAction: input.correctiveAction,
  })

  appendMockAuditEvent({
    area: 'Feedback',
    action: `Recorded ${id} for ${order.id}`,
    entityType: 'feedback',
    entityId: id,
  })

  return getExperienceIntelligenceWorkspace()
}

export function updateMockFeedback(
  feedbackId: string,
  input: UpdateFeedbackInput,
): ExperienceIntelligenceWorkspace {
  const item = feedback.find((candidate) => candidate.id === feedbackId)
  if (!item) return getExperienceIntelligenceWorkspace()

  item.status = input.status
  item.correctiveAction = input.correctiveAction

  if (input.followUpAt) item.followUpAt = input.followUpAt
  else delete item.followUpAt

  appendMockAuditEvent({
    area: 'Feedback',
    action: `Updated ${feedbackId} to ${input.status}`,
    entityType: 'feedback',
    entityId: feedbackId,
  })

  return getExperienceIntelligenceWorkspace()
}
""",
)

# Add shared audit import to domain stores.
for path, anchor in [
    (
        "src/modules/commercial/mocks/commercial.mock-db.ts",
        "import { formatCurrency } from '@/shared/lib/formatters'\n",
    ),
    (
        "src/modules/fulfillment/mocks/fulfillment.mock-db.ts",
        "} from '../workspaces/fulfillment-workflow.rules'\n",
    ),
    (
        "src/modules/specialized-services/mocks/specialized-services.mock-db.ts",
        "import { buildPlots } from '../workspaces/specialized-services.rules'\n",
    ),
    (
        "src/modules/service-administration/mocks/service-administration.mock-db.ts",
        "} from '../types/service-administration.types'\n",
    ),
]:
    text = read(path)
    import_line = "import { appendMockAuditEvent } from '@/shared/audit/mock-audit-store'\n"
    if import_line not in text:
        if anchor not in text:
            raise SystemExit(f"Audit import anchor missing: {path}")
        text = text.replace(anchor, anchor + import_line, 1)
        write(path, text)

# Commercial.
insert_before_last_return_in_function(
    "src/modules/commercial/mocks/commercial.mock-db.ts",
    "createMockInvoice",
    "return getCommercialWorkspace()",
    """  appendMockAuditEvent({
    area: 'Invoice',
    action: `Created ${id} from ${quotation.id}`,
    entityType: 'invoice',
    entityId: id,
  })""",
)
insert_before_last_return_in_function(
    "src/modules/commercial/mocks/commercial.mock-db.ts",
    "recordMockPayment",
    "return getCommercialWorkspace()",
    """  appendMockAuditEvent({
    area: 'Payment',
    action: `Recorded ${formatCurrency(input.amount)} against ${invoice.id}`,
    entityType: 'invoice',
    entityId: invoice.id,
  })""",
)
insert_before_last_return_in_function(
    "src/modules/commercial/mocks/commercial.mock-db.ts",
    "decideMockApproval",
    "return getCommercialWorkspace()",
    """  appendMockAuditEvent({
    area: 'Approval',
    action: `${approval.id} ${approval.status.toLowerCase()}: ${approval.entityId}`,
    entityType: 'approval',
    entityId: approval.id,
  })""",
)
insert_before_last_return_in_function(
    "src/modules/commercial/mocks/commercial.mock-db.ts",
    "createMockQuotation",
    "return getCommercialWorkspace()",
    """  appendMockAuditEvent({
    area: 'Quotation',
    action: `Created ${id} for ${source.id}`,
    entityType: 'quotation',
    entityId: id,
  })""",
)
insert_before_last_return_in_function(
    "src/modules/commercial/mocks/commercial.mock-db.ts",
    "updateMockQuotation",
    "return getCommercialWorkspace()",
    """  appendMockAuditEvent({
    area: 'Quotation',
    action: `Updated ${id}: ${action}`,
    entityType: 'quotation',
    entityId: id,
  })""",
)
insert_before_last_return_in_function(
    "src/modules/commercial/mocks/commercial.mock-db.ts",
    "createMockServiceRequest",
    "return getCommercialWorkspace()",
    """  appendMockAuditEvent({
    area: 'Request',
    action: `Created ${id} for ${input.client}`,
    entityType: 'request',
    entityId: id,
  })""",
)
insert_before_last_return_in_function(
    "src/modules/commercial/mocks/commercial.mock-db.ts",
    "updateMockServiceRequest",
    "return getCommercialWorkspace()",
    """  appendMockAuditEvent({
    area: 'Request',
    action: `Updated ${id}${input.status ? ` to ${input.status}` : ''}`,
    entityType: 'request',
    entityId: id,
  })""",
)

# Fulfillment.
for func, snippet in [
    ("ensureMockOrderFromCommercialSource", """  const created = orders.find((order) => order.invoiceId === input.invoiceId)
  if (created) {
    appendMockAuditEvent({
      area: 'Order',
      action: `Created ${created.id} from paid commercial work`,
      entityType: 'order',
      entityId: created.id,
    })
  }"""),
    ("createMockOrder", """  appendMockAuditEvent({
    area: 'Order',
    action: `Created ${id} for ${input.client}`,
    entityType: 'order',
    entityId: id,
  })"""),
    ("updateMockOrder", """  appendMockAuditEvent({
    area: 'Order',
    action: `Updated ${orderId}`,
    entityType: 'order',
    entityId: orderId,
  })"""),
    ("advanceMockOrder", """  appendMockAuditEvent({
    area: 'Order',
    action: `Advanced ${orderId} to ${order.stage}`,
    entityType: 'order',
    entityId: orderId,
  })"""),
    ("addMockOrderUpdate", """  appendMockAuditEvent({
    area: 'Order',
    action: `Recorded progress update for ${order.id}`,
    entityType: 'order',
    entityId: order.id,
  })"""),
    ("addMockMilestone", """  appendMockAuditEvent({
    area: 'Milestone',
    action: `Added milestone "${input.name.trim()}" to ${order.id}`,
    entityType: 'order',
    entityId: order.id,
  })"""),
    ("createMockTask", """  appendMockAuditEvent({
    area: 'Task',
    action: `Created ${id} for ${input.orderId}`,
    entityType: 'task',
    entityId: id,
  })"""),
    ("updateMockTask", """  appendMockAuditEvent({
    area: 'Task',
    action: `${taskId}: ${input.action}`,
    entityType: 'task',
    entityId: taskId,
  })"""),
    ("createMockDeliverable", """  appendMockAuditEvent({
    area: 'Deliverable',
    action: `Created ${id} for ${input.orderId}`,
    entityType: 'deliverable',
    entityId: id,
  })"""),
    ("decideMockDeliverable", """  appendMockAuditEvent({
    area: 'Deliverable',
    action: `${input.action === 'approve' ? 'Approved' : 'Rejected'} ${deliverableId}`,
    entityType: 'deliverable',
    entityId: deliverableId,
  })"""),
]:
    insert_before_last_return_in_function(
        "src/modules/fulfillment/mocks/fulfillment.mock-db.ts",
        func,
        "return getFulfillmentWorkspace()",
        snippet,
    )

# Specialized.
insert_before_last_return_in_function(
    "src/modules/specialized-services/mocks/specialized-services.mock-db.ts",
    "createMockEstate",
    "return getSpecializedWorkspace()",
    """  const created = estates.at(-1)
  if (created) {
    appendMockAuditEvent({
      area: 'Estate',
      action: `Created ${created.name}`,
      entityType: 'estate',
      entityId: created.id,
    })
  }""",
)
insert_before_last_return_in_function(
    "src/modules/specialized-services/mocks/specialized-services.mock-db.ts",
    "updateMockPlot",
    "return getSpecializedWorkspace()",
    """  if (p) {
    appendMockAuditEvent({
      area: 'Plot',
      action: `Updated ${input.estateId} plot ${input.plotNo} to ${input.status}`,
      entityType: 'plot',
      entityId: `${input.estateId}-${input.plotNo}`,
    })
  }""",
)
insert_before_last_return_in_function(
    "src/modules/specialized-services/mocks/specialized-services.mock-db.ts",
    "createMockBrokerageProperty",
    "return getSpecializedWorkspace()",
    """  const created = brokerage[0]
  if (created) {
    appendMockAuditEvent({
      area: 'Property',
      action: `Created brokerage listing ${created.id}`,
      entityType: 'property',
      entityId: created.id,
    })
  }""",
)

# Service Administration: focus on major save/create operations.
# createMockServiceWizard returns workspace.
insert_before_last_return_in_function(
    "src/modules/service-administration/mocks/service-administration.mock-db.ts",
    "createMockServiceWizard",
    "return getServiceAdministrationWorkspace()",
    """  appendMockAuditEvent({
    area: 'Service',
    action: `Created service ${serviceId}`,
    entityType: 'service',
    entityId: serviceId,
  })""",
)
insert_before_last_return_in_function(
    "src/modules/service-administration/mocks/service-administration.mock-db.ts",
    "configureMockService",
    "return getServiceAdministrationWorkspace()",
    """  appendMockAuditEvent({
    area: 'Service',
    action: `Updated service ${input.id}`,
    entityType: 'service',
    entityId: input.id,
  })""",
)
insert_before_last_return_in_function(
    "src/modules/service-administration/mocks/service-administration.mock-db.ts",
    "saveMockBranchActivationMatrix",
    "return getServiceAdministrationWorkspace()",
    """  appendMockAuditEvent({
    area: 'Branch Activation',
    action: `Updated ${input.updates.length} service/branch activation records`,
  })""",
)

# ---------------------------------------------------------------------------
# D. PERMISSION-PATH REGRESSION + ACTION-LEVEL GATES
# ---------------------------------------------------------------------------
write(
    "src/app/permissions/action-permissions.ts",
    """import type { AuthUser } from '@/app/auth'

import { PERMISSIONS, hasPermission } from './permissions'

export const APP_ACTIONS = {
  serviceCreate: 'service.create',
  serviceUpdate: 'service.update',
  requestCreate: 'request.create',
  requestUpdate: 'request.update',
  quoteCreate: 'quote.create',
  quoteApprove: 'quote.approve',
  invoiceCreate: 'invoice.create',
  paymentConfirm: 'payment.confirm',
  approvalAct: 'approval.act',
  orderUpdate: 'order.update',
  taskUpdate: 'task.update',
  deliverableUpdate: 'deliverable.update',
  deliverableApprove: 'deliverable.approve',
} as const

export type AppAction = keyof typeof APP_ACTIONS

const actionPermissions = {
  serviceCreate: PERMISSIONS.serviceCreate,
  serviceUpdate: PERMISSIONS.serviceUpdate,
  requestCreate: PERMISSIONS.requestCreate,
  requestUpdate: PERMISSIONS.requestUpdate,
  quoteCreate: PERMISSIONS.quoteCreate,
  quoteApprove: PERMISSIONS.quoteApprove,
  invoiceCreate: PERMISSIONS.invoiceCreate,
  paymentConfirm: PERMISSIONS.paymentConfirm,
  approvalAct: PERMISSIONS.approvalAct,
  orderUpdate: PERMISSIONS.orderUpdate,
  taskUpdate: PERMISSIONS.taskUpdate,
  deliverableUpdate: PERMISSIONS.deliverableUpdate,
  deliverableApprove: PERMISSIONS.deliverableApprove,
} as const

export function canPerformAction(user: AuthUser | null, action: AppAction): boolean {
  return hasPermission(user, actionPermissions[action])
}
""",
)

p = "src/app/permissions/index.ts"
text = read(p)
export_line = "export { APP_ACTIONS, canPerformAction } from './action-permissions'\n"
if export_line not in text:
    text = export_line + text
write(p, text)

write(
    "src/app/permissions/action-permissions.test.ts",
    """import { describe, expect, it } from 'vitest'

import type { AuthUser } from '@/app/auth'

import { PERMISSIONS } from './permissions'
import { canPerformAction } from './action-permissions'

function user(permissions: AuthUser['permissions']): AuthUser {
  return {
    id: '1',
    name: 'Staff',
    email: 'staff@bomach.local',
    username: 'staff',
    initials: 'ST',
    role: 'UNKNOWN',
    roleLabel: 'Backend Role',
    kind: 'staff',
    permissions,
    backendPermissions: [...permissions],
    isVerified: true,
  }
}

describe('action permissions', () => {
  it('does not infer write access from role or read access', () => {
    const staff = user([PERMISSIONS.invoiceRead, PERMISSIONS.orderRead])
    expect(canPerformAction(staff, 'paymentConfirm')).toBe(false)
    expect(canPerformAction(staff, 'orderUpdate')).toBe(false)
  })

  it('allows only the explicit backend capability', () => {
    const staff = user([
      PERMISSIONS.invoiceRead,
      PERMISSIONS.paymentConfirm,
      PERMISSIONS.orderRead,
      PERMISSIONS.orderUpdate,
    ])

    expect(canPerformAction(staff, 'paymentConfirm')).toBe(true)
    expect(canPerformAction(staff, 'orderUpdate')).toBe(true)
    expect(canPerformAction(staff, 'deliverableApprove')).toBe(false)
  })
})
""",
)

# Commercial page top-level action gates.
text = read(commercial_page)
if "canPerformAction" not in text:
    text = text.replace(
        "import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'\n",
        "import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'\n"
        "import { canPerformAction } from '@/app/permissions'\n"
        "import { useAuth } from '@/app/auth'\n",
        1,
    )
if "const { user } = useAuth()" not in text:
    text = text.replace(
        "  const navigate = useNavigate()\n",
        "  const navigate = useNavigate()\n  const { user } = useAuth()\n",
        1,
    )
if "const canCreatePrimary =" not in text:
    anchor = "  const page = metadata[section]\n"
    block = """  const canCreatePrimary =
    section === 'service-requests' || section === 'approvals'
      ? canPerformAction(user, 'requestCreate')
      : section === 'quotations'
        ? canPerformAction(user, 'quoteCreate')
        : canPerformAction(user, 'invoiceCreate')

  const canConfirmPayment = canPerformAction(user, 'paymentConfirm')
  const canActApproval = canPerformAction(user, 'approvalAct')

"""
    text = text.replace(anchor, anchor + block, 1)
text = text.replace(
    "        primaryAction={\n          <PrototypeButton",
    "        primaryAction={\n          canCreatePrimary ? (\n          <PrototypeButton",
    1,
)
primary_close = """          </PrototypeButton>
        }
      />"""
if primary_close in text and "          ) : undefined\n        }\n      />" not in text:
    text = text.replace(
        primary_close,
        """          </PrototypeButton>
          ) : undefined
        }
      />""",
        1,
    )

# Pass permission props to finance/approval workspaces.
text = text.replace(
    "          onRecordPayment={(input) => recordPayment.mutate(input)}\n",
    "          canConfirmPayment={canConfirmPayment}\n"
    "          onRecordPayment={(input) => recordPayment.mutate(input)}\n",
)
text = text.replace(
    "          onDecide={(input) => decideApproval.mutate(input)}\n",
    "          canAct={canActApproval}\n"
    "          onDecide={(input) => decideApproval.mutate(input)}\n",
)
write(commercial_page, text)

# Invoice action gate.
invoice_ws = "src/modules/commercial/workspaces/InvoiceDetailWorkspace.tsx"
text = read(invoice_ws)
text = text.replace(
    "  onClose,\n  onRecordPayment,\n",
    "  onClose,\n  canConfirmPayment,\n  onRecordPayment,\n",
)
text = text.replace(
    "  onClose: () => void\n  onRecordPayment:",
    "  onClose: () => void\n  canConfirmPayment: boolean\n  onRecordPayment:",
)
text = text.replace(
    "{invoice.balance > 0 ? (",
    "{invoice.balance > 0 && canConfirmPayment ? (",
)
# There are two occurrences; replace all.
text = text.replace(
    "{invoice.balance > 0 ? (",
    "{invoice.balance > 0 && canConfirmPayment ? (",
)
write(invoice_ws, text)

# Approval action gate.
approval_ws = "src/modules/commercial/workspaces/ApprovalDecisionWorkspace.tsx"
text = read(approval_ws)
text = text.replace(
    "  onClose,\n  onDecide,\n",
    "  onClose,\n  canAct,\n  onDecide,\n",
)
text = text.replace(
    "  onClose: () => void\n  onDecide:",
    "  onClose: () => void\n  canAct: boolean\n  onDecide:",
)
text = text.replace(
    "{approval.status === 'Pending' ? (",
    "{approval.status === 'Pending' && canAct ? (",
)
# Applies both decision-note and footer. This is desired: readers see decision history, not editable decision UI.
write(approval_ws, text)

# Fulfillment action gates.
text = read(fulfillment_page)
if "canPerformAction" not in text:
    text = text.replace(
        "import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'\n",
        "import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'\n"
        "import { canPerformAction } from '@/app/permissions'\n"
        "import { useAuth } from '@/app/auth'\n",
        1,
    )
if "const { user } = useAuth()" not in text:
    text = text.replace(
        "  const queryClient = useQueryClient()\n",
        "  const queryClient = useQueryClient()\n  const { user } = useAuth()\n",
        1,
    )
if "const canCreatePrimary =" not in text:
    anchor = "  const primaryLabel =\n"
    block = """  const canUpdateOrder = canPerformAction(user, 'orderUpdate')
  const canUpdateTask = canPerformAction(user, 'taskUpdate')
  const canUpdateDeliverable = canPerformAction(user, 'deliverableUpdate')
  const canApproveDeliverable = canPerformAction(user, 'deliverableApprove')
  const canCreatePrimary =
    section === 'service-orders'
      ? canUpdateOrder
      : section === 'execution-tasks'
        ? canUpdateTask
        : canUpdateDeliverable

"""
    text = text.replace(anchor, block + anchor, 1)

text = text.replace(
    "        primaryAction={\n          <PrototypeButton",
    "        primaryAction={\n          canCreatePrimary ? (\n          <PrototypeButton",
    1,
)
if primary_close in text and "          ) : undefined\n        }\n      />" not in text:
    text = text.replace(
        primary_close,
        """          </PrototypeButton>
          ) : undefined
        }
      />""",
        1,
    )

text = text.replace(
    "          saving={decideDeliverable.isPending}\n",
    "          saving={decideDeliverable.isPending}\n"
    "          canApprove={canApproveDeliverable}\n",
)
text = text.replace(
    "          saving={updateTask.isPending}\n",
    "          saving={updateTask.isPending}\n"
    "          canEdit={canUpdateTask}\n",
)
text = text.replace(
    "          saving={busy}\n",
    "          saving={busy}\n"
    "          canEditOrder={canUpdateOrder}\n"
    "          canCreateTask={canUpdateTask}\n"
    "          canCreateDeliverable={canUpdateDeliverable}\n",
)
write(fulfillment_page, text)

# Deliverable approve/reject gate.
deliverable_ws = "src/modules/fulfillment/workspaces/DeliverableDetailWorkspace.tsx"
text = read(deliverable_ws)
text = text.replace(
    "  saving,\n  onClose,\n",
    "  saving,\n  canApprove,\n  onClose,\n",
)
text = text.replace(
    "  saving: boolean\n  onClose:",
    "  saving: boolean\n  canApprove: boolean\n  onClose:",
)
text = text.replace(
    "{deliverable.status === 'Under Review' ? (",
    "{deliverable.status === 'Under Review' && canApprove ? (",
)
write(deliverable_ws, text)

# Task edit gate. Keep read-only content visible; hide mutation surfaces.
task_ws = "src/modules/fulfillment/workspaces/TaskDetailWorkspace.tsx"
text = read(task_ws)
text = text.replace(
    "  saving,\n  onClose,\n",
    "  saving,\n  canEdit,\n  onClose,\n",
)
text = text.replace(
    "  saving: boolean\n  onClose:",
    "  saving: boolean\n  canEdit: boolean\n  onClose:",
)
text = text.replace(
    '<div className="fulfillment-inline-evidence">',
    '{canEdit ? <div className="fulfillment-inline-evidence">',
    1,
)
text = text.replace(
    """                </div>
              </section>

              <section className="fulfillment-card">
                <header className="fulfillment-card-header">
                  <div>
                    <div className="fulfillment-card-title">Task Activity</div>""",
    """                </div> : null}
              </section>

              <section className="fulfillment-card">
                <header className="fulfillment-card-header">
                  <div>
                    <div className="fulfillment-card-title">Task Activity</div>""",
    1,
)
# Wrap inline activity entry.
text = text.replace(
    '<div className="fulfillment-inline-create">\n                  <input\n                    placeholder="Add task activity..."',
    '{canEdit ? <div className="fulfillment-inline-create">\n                  <input\n                    placeholder="Add task activity..."',
    1,
)
text = text.replace(
    """                  </button>
                </div>
              </section>
            </div>

            <aside>""",
    """                  </button>
                </div> : null}
              </section>
            </div>

            <aside>""",
    1,
)
# Hide all aside controls from read-only users while preserving task overview.
text = text.replace(
    "            <aside>\n",
    "            {canEdit ? <aside>\n",
    1,
)
text = text.replace(
    """            </aside>
          </div>
        </div>""",
    """            </aside> : null}
          </div>
        </div>""",
    1,
)
write(task_ws, text)

# Order control workspace: hide mutation buttons/forms for read-only users.
order_ws = "src/modules/fulfillment/workspaces/OrderControlRoomWorkspace.tsx"
text = read(order_ws)
text = text.replace(
    "  saving,\n  onClose,\n",
    "  saving,\n  canEditOrder,\n  canCreateTask,\n  canCreateDeliverable,\n  onClose,\n",
)
text = text.replace(
    "  saving: boolean\n  onClose:",
    "  saving: boolean\n  canEditOrder: boolean\n  canCreateTask: boolean\n  canCreateDeliverable: boolean\n  onClose:",
)
# Targeted button/form conditions.
text = text.replace(
    """                    <button
                      type="button"
                      className="fulfillment-btn fulfillment-btn-primary"
                      onClick={() => setShowMilestone((value) => !value)}
                    >
                      Add Milestone
                    </button>""",
    """                    {canEditOrder ? (
                      <button
                        type="button"
                        className="fulfillment-btn fulfillment-btn-primary"
                        onClick={() => setShowMilestone((value) => !value)}
                      >
                        Add Milestone
                      </button>
                    ) : null}""",
)
text = text.replace("{showMilestone ? (", "{showMilestone && canEditOrder ? (")
text = text.replace(
    """                    <button
                      type="button"
                      className="fulfillment-btn fulfillment-btn-small"
                      onClick={() => setShowTask(true)}
                    >
                      New Task
                    </button>""",
    """                    {canCreateTask ? (
                      <button
                        type="button"
                        className="fulfillment-btn fulfillment-btn-small"
                        onClick={() => setShowTask(true)}
                      >
                        New Task
                      </button>
                    ) : null}""",
)
text = text.replace(
    """                    <button
                      type="button"
                      className="fulfillment-btn"
                      onClick={() => setShowUpdate(true)}
                    >
                      Add Update
                    </button>""",
    """                    {canEditOrder ? (
                      <button
                        type="button"
                        className="fulfillment-btn"
                        onClick={() => setShowUpdate(true)}
                      >
                        Add Update
                      </button>
                    ) : null}""",
)
# Order controls card only for editors.
text = text.replace(
    """                <section className="fulfillment-card">
                  <header className="fulfillment-card-header">
                    <div className="fulfillment-card-title">Order Controls</div>
                  </header>""",
    """                {canEditOrder ? (
                <section className="fulfillment-card">
                  <header className="fulfillment-card-header">
                    <div className="fulfillment-card-title">Order Controls</div>
                  </header>""",
    1,
)
# Close first order controls section before financial.
text = text.replace(
    """                </section>

                <section className="fulfillment-card">
                  <header className="fulfillment-card-header">
                    <div className="fulfillment-card-title">Financial Summary</div>""",
    """                </section>
                ) : null}

                <section className="fulfillment-card">
                  <header className="fulfillment-card-header">
                    <div className="fulfillment-card-title">Financial Summary</div>""",
    1,
)
# Add Deliverable quick action gated; leave prototype placeholders request approval/feedback visible only to order editors.
text = text.replace(
    """                  <button
                    type="button"
                    className="fulfillment-btn fulfillment-btn-block"
                    onClick={() => onFutureAction('Add Deliverable')}
                  >
                    Add Deliverable
                  </button>""",
    """                  {canCreateDeliverable ? (
                    <button
                      type="button"
                      className="fulfillment-btn fulfillment-btn-block"
                      onClick={() => onFutureAction('Add Deliverable')}
                    >
                      Add Deliverable
                    </button>
                  ) : null}""",
)
# Remaining quick mutations belong to order editors.
text = text.replace(
    """                  <button
                    type="button"
                    className="fulfillment-btn fulfillment-btn-block fulfillment-top-gap"
                    onClick={() => onFutureAction('Request Client Approval')}
                  >""",
    """                  {canEditOrder ? (
                    <>
                  <button
                    type="button"
                    className="fulfillment-btn fulfillment-btn-block fulfillment-top-gap"
                    onClick={() => onFutureAction('Request Client Approval')}
                  >""",
)
text = text.replace(
    """                    Record Feedback
                  </button>
                </section>""",
    """                    Record Feedback
                  </button>
                    </>
                  ) : null}
                </section>""",
    1,
)
text = text.replace("{showUpdate ? (", "{showUpdate && canEditOrder ? (")
text = text.replace("{showTask ? (", "{showTask && canCreateTask ? (")
write(order_ws, text)

# ---------------------------------------------------------------------------
# E. STATE REVIEW + REGRESSION TESTS
# ---------------------------------------------------------------------------
write(
    "src/shared/navigation/record-links.test.ts",
    """import { describe, expect, it } from 'vitest'

import { getRecordDestination } from './record-links'

describe('record deep links', () => {
  it('maps core business entities to an exact route and record search param', () => {
    expect(getRecordDestination('request', 'REQ-1')).toEqual({
      section: 'service-requests',
      search: { request: 'REQ-1' },
    })
    expect(getRecordDestination('order', 'ORD-1')).toEqual({
      section: 'service-orders',
      search: { order: 'ORD-1' },
    })
    expect(getRecordDestination('deliverable', 'DEL-1')).toEqual({
      section: 'deliverables',
      search: { deliverable: 'DEL-1' },
    })
    expect(getRecordDestination('feedback', 'FDB-1')).toEqual({
      section: 'feedback-quality',
      search: { feedback: 'FDB-1' },
    })
  })

  it('does not manufacture a route for an unsupported entity type', () => {
    expect(getRecordDestination('unknown', '1')).toBeNull()
  })
})
""",
)

write(
    "src/app/notifications/notification.mapper.test.ts",
    """import { describe, expect, it } from 'vitest'

import { mapNotificationPayload } from './notification.mapper'

describe('notification transport mapper', () => {
  it('maps a backend envelope without creating business notifications locally', () => {
    expect(
      mapNotificationPayload({
        results: [
          {
            id: 'N1',
            title: 'Deliverable awaiting review',
            message: 'DEL-701 requires review',
            created_at: '2026-08-07T11:00:00Z',
            is_read: false,
            severity: 'warning',
            entity_type: 'deliverable',
            entity_id: 'DEL-701',
          },
        ],
      }),
    ).toEqual([
      {
        id: 'N1',
        title: 'Deliverable awaiting review',
        description: 'DEL-701 requires review',
        timestamp: '2026-08-07T11:00:00Z',
        read: false,
        tone: 'warning',
        entityType: 'deliverable',
        entityId: 'DEL-701',
      },
    ])
  })
})
""",
)

write(
    "docs/ui-rebuild/updates/UI_4_04_A_E_CROSS_APP_INTEGRATION.md",
    """# UI-4.04A–E — Cross-App Integration

## A — Internal record linking

The generic `/app/$section` route now validates record search parameters for
requests, quotations, invoices, approvals, orders, tasks, deliverables and
feedback.

Examples:

```text
/app/service-orders?order=ORD-260710-002
/app/execution-tasks?task=TSK-704
/app/deliverables?deliverable=DEL-701
/app/feedback-quality?feedback=FDB-003
```

`RecordLink` keeps visible prototype columns unchanged while making referenced
records navigable. Audit and notification surfaces resolve record destinations
through the same mapping.

## B — Notification API integration

Notification business logic remains backend-owned.

The old local `mockNotifications` source has been removed. `NotificationPanel`
uses TanStack Query and an API adapter. The exact backend notification contract
was not present in the current repository at implementation time, so endpoint
paths are configuration-only and have no invented defaults:

- `VITE_NOTIFICATION_LIST_PATH`
- `VITE_NOTIFICATION_MARK_READ_PATH` (`{id}` placeholder supported)
- `VITE_NOTIFICATION_MARK_ALL_READ_PATH`

Until those values are configured from the published backend contract, the
drawer reports that backend configuration is pending rather than generating
fake notifications.

The transport mapper is deliberately isolated and should be replaced by exact
OpenAPI-generated DTO mapping when the notification schema is finalized.

## C — Full audit instrumentation

The append-only mock audit store moved to `src/shared/audit` so older business
modules do not depend on the Experience & Intelligence UI module.

Major mutations now append audit events from their mock-domain layer:

- service creation/configuration and branch activation;
- request, quotation, approval, invoice and payment mutations;
- order, milestone, task and deliverable mutations;
- estate, plot and brokerage-property mutations;
- feedback and quality follow-up.

React components do not push audit rows directly.

## D — Permission-path regression

Backend permissions remain authoritative. A shared action-permission map
separates read access from write/decision capabilities.

Key action gates now cover:

- request/quotation/invoice creation;
- payment confirmation;
- approval decisions;
- order updates;
- task updates;
- deliverable creation/update;
- deliverable approval.

Read-only users can still open permitted records but do not receive the
corresponding mutation controls.

## E — Loading / empty / error review

Existing module pages already use shared `DashboardSkeleton`, `ErrorState`,
empty-register rows/cards and mutation toasts.

This slice additionally replaces the notification panel's local always-success
state with:

- loading skeletons;
- retryable backend error;
- explicit backend-contract-not-configured state;
- empty notification state;
- mutation pending state.

Feedback, Reports and Audit already include their own empty states, while
Commercial, Fulfillment, Service Administration and Specialized Services retain
their established page loading/error handling.
""",
)

# Remove accidental stale local notification export/imports if any.
for p in Path("src").rglob("*.ts*"):
    if p.as_posix().endswith("notification.data.ts"):
        continue
    content = p.read_text()
    if "mockNotifications" in content:
        raise SystemExit(f"Stale mockNotifications reference remains in {p}")

PY

npm run format
npm run check
npm run test -- --run
npm run build:storybook

echo
echo "UI-4.04A–E applied and verification passed."
