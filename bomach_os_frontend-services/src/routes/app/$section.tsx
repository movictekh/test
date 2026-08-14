import { lazy, Suspense } from 'react'
import { createFileRoute, Navigate } from '@tanstack/react-router'

import { useAuth } from '@/app/auth'
import { findNavigationItemByPath, operationsNavigation } from '@/app/navigation'
import { hasPermissions, PERMISSIONS, requireRoutePermission } from '@/app/permissions'
import { SectionLoadingState } from '@/app/loading/SectionLoadingState'
import type { AppRecordSearch } from '@/shared/navigation'
import type { ServiceAdministrationSection } from '@/modules/service-administration'
import { ModuleShellPage } from '@/modules/foundation/pages/ModuleShellPage'

const ServiceAdministrationSectionPage = lazy(() =>
  import('@/modules/service-administration').then((module) => ({
    default: module.ServiceAdministrationSectionPage,
  })),
)

const ServiceRequestsLivePage = lazy(() =>
  import('@/modules/commercial/pages/ServiceRequestsLivePage').then((module) => ({
    default: module.ServiceRequestsLivePage,
  })),
)

const QuotationsLivePage = lazy(() =>
  import('@/modules/commercial/pages/QuotationsLivePage').then((module) => ({
    default: module.QuotationsLivePage,
  })),
)

const InvoicesPaymentsLivePage = lazy(() =>
  import('@/modules/commercial/pages/InvoicesPaymentsLivePage').then((module) => ({
    default: module.InvoicesPaymentsLivePage,
  })),
)

const ApprovalsLivePage = lazy(() =>
  import('@/modules/commercial/pages/ApprovalsLivePage').then((module) => ({
    default: module.ApprovalsLivePage,
  })),
)

const ServiceOrdersLivePage = lazy(() =>
  import('@/modules/fulfillment/pages/ServiceOrdersLivePage').then((module) => ({
    default: module.ServiceOrdersLivePage,
  })),
)

const ExecutionTasksLivePage = lazy(() =>
  import('@/modules/fulfillment/pages/ExecutionTasksLivePage').then((module) => ({
    default: module.ExecutionTasksLivePage,
  })),
)

const DeliverablesLivePage = lazy(() =>
  import('@/modules/fulfillment/pages/DeliverablesLivePage').then((module) => ({
    default: module.DeliverablesLivePage,
  })),
)

const RealEstateInventoryLivePage = lazy(() =>
  import('@/modules/specialized-services/pages/RealEstateInventoryLivePage').then((module) => ({
    default: module.RealEstateInventoryLivePage,
  })),
)

const SpecializedOperationsLivePage = lazy(() =>
  import('@/modules/specialized-services/pages/SpecializedOperationsLivePage').then((module) => ({
    default: module.SpecializedOperationsLivePage,
  })),
)

const FeedbackQualityLivePage = lazy(() =>
  import('@/modules/experience-intelligence/pages/FeedbackQualityLivePage').then((module) => ({
    default: module.FeedbackQualityLivePage,
  })),
)

const ReportsAnalyticsLivePage = lazy(() =>
  import('@/modules/experience-intelligence/pages/ReportsAnalyticsLivePage').then((module) => ({
    default: module.ReportsAnalyticsLivePage,
  })),
)

const serviceAdministrationSections = new Set<ServiceAdministrationSection>([
  'service-catalogue',
  'calculator-library',
  'request-form-builder',
  'workflow-designer',
  'branch-activation',
])

export type AppSectionSearch = AppRecordSearch & {
  create?: string
  search?: string
  status?: string
  paymentStatus?: string
  source?: string
  highValue?: boolean
  division?: string
  priority?: string
  branch?: string
  service?: string
  deliverableType?: string
  clientVisible?: string
  feedbackType?: string
  ratingMin?: number
  estate?: string
  property?: string
  page?: number
}

export function parseRecordSearch(search: Record<string, unknown>): AppSectionSearch {
  const stringValue = (value: unknown): string | undefined =>
    typeof value === 'string' && value.trim() ? value.trim() : undefined

  const identifierValue = (value: unknown): string | undefined => {
    const raw = stringValue(value)
    if (!raw) return undefined

    const first = raw.at(0)
    const last = raw.at(-1)
    const unquoted =
      raw.length >= 2 && ((first === '"' && last === '"') || (first === "'" && last === "'"))
        ? raw.slice(1, -1).trim()
        : raw

    return unquoted || undefined
  }

  const result: AppSectionSearch = {}
  const request = identifierValue(search.request)
  const quotation = identifierValue(search.quotation)
  const invoice = identifierValue(search.invoice)
  const approval = identifierValue(search.approval)
  const order = identifierValue(search.order)
  const task = identifierValue(search.task)
  const deliverable = identifierValue(search.deliverable)
  const estate = identifierValue(search.estate)
  const property = identifierValue(search.property) ?? identifierValue(search.plot)
  const feedback = identifierValue(search.feedback)
  const create = stringValue(search.create)

  const catalogueSearch = stringValue(search.search)
  const catalogueStatus = stringValue(search.status)
  const orderPaymentStatus = stringValue(search.paymentStatus)
  const approvalSource = stringValue(search.source)
  const approvalHighValue =
    search.highValue === true ||
    (typeof search.highValue === 'string' && search.highValue.toLowerCase() === 'true')
  const catalogueDivision = stringValue(search.division)
  const requestPriority = stringValue(search.priority)
  const requestBranch = stringValue(search.branch)
  const requestService = identifierValue(search.service)
  const deliverableType = stringValue(search.deliverableType)
  const clientVisible = stringValue(search.clientVisible)
  const feedbackType = stringValue(search.feedbackType)
  const rawRatingMin =
    typeof search.ratingMin === 'number'
      ? search.ratingMin
      : typeof search.ratingMin === 'string'
        ? Number(search.ratingMin)
        : undefined
  const ratingMin =
    rawRatingMin !== undefined &&
    Number.isInteger(rawRatingMin) &&
    rawRatingMin >= 1 &&
    rawRatingMin <= 5
      ? rawRatingMin
      : undefined
  const rawPage =
    typeof search.page === 'number'
      ? search.page
      : typeof search.page === 'string'
        ? Number(search.page)
        : undefined
  const cataloguePage =
    rawPage !== undefined && Number.isInteger(rawPage) && rawPage > 0 ? rawPage : undefined

  if (request) result.request = request
  if (quotation) result.quotation = quotation
  if (invoice) result.invoice = invoice
  if (approval) result.approval = approval
  if (order) result.order = order
  if (task) result.task = task
  if (deliverable) result.deliverable = deliverable
  if (estate) result.estate = estate
  if (property) result.property = property
  if (feedback) result.feedback = feedback
  if (create) result.create = create

  if (catalogueSearch) result.search = catalogueSearch
  if (catalogueStatus) result.status = catalogueStatus
  if (orderPaymentStatus) result.paymentStatus = orderPaymentStatus
  if (approvalSource) result.source = approvalSource
  if (approvalHighValue) result.highValue = true
  if (catalogueDivision) result.division = catalogueDivision
  if (requestPriority) result.priority = requestPriority
  if (requestBranch) result.branch = requestBranch
  if (requestService) result.service = requestService
  if (deliverableType) result.deliverableType = deliverableType
  if (clientVisible === 'true' || clientVisible === 'false') result.clientVisible = clientVisible
  if (feedbackType) result.feedbackType = feedbackType
  if (ratingMin) result.ratingMin = ratingMin
  if (cataloguePage) result.page = cataloguePage

  return result
}

function formatSectionTitle(section: string): string {
  return section
    .split('-')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export const Route = createFileRoute('/app/$section')({
  validateSearch: parseRecordSearch,
  beforeLoad: ({ context, location }) => {
    const matchingItem = findNavigationItemByPath(operationsNavigation, location.pathname)

    return requireRoutePermission({
      auth: context.auth,
      permissions: matchingItem?.permissions ?? [PERMISSIONS.dashboardView],
      locationHref: location.href,
    })
  },
  component: AppShellRoute,
})

function AppShellRoute() {
  const { section } = Route.useParams()
  const auth = useAuth()
  const matchingItem = findNavigationItemByPath(operationsNavigation, `/app/${section}`)
  const requiredPermissions = matchingItem?.permissions ?? [PERMISSIONS.dashboardView]

  if (auth.isLoading) {
    return <SectionLoadingState section={section} />
  }

  if (!auth.isAuthenticated || !auth.user) {
    return <Navigate to="/login" replace />
  }

  if (!hasPermissions(auth.user, requiredPermissions)) {
    return <Navigate to="/forbidden" replace />
  }

  return (
    <Suspense fallback={<SectionLoadingState section={section} />}>
      <AppShellRouteContent />
    </Suspense>
  )
}

function AppShellRouteContent() {
  const { section } = Route.useParams()
  const recordSearch = Route.useSearch()

  if (section === 'service-requests') return <ServiceRequestsLivePage recordSearch={recordSearch} />
  if (section === 'quotations') return <QuotationsLivePage recordSearch={recordSearch} />
  if (section === 'invoices-payments')
    return <InvoicesPaymentsLivePage recordSearch={recordSearch} />
  if (section === 'approvals') return <ApprovalsLivePage recordSearch={recordSearch} />
  if (section === 'service-orders') return <ServiceOrdersLivePage recordSearch={recordSearch} />
  if (section === 'execution-tasks') return <ExecutionTasksLivePage recordSearch={recordSearch} />
  if (section === 'deliverables') return <DeliverablesLivePage recordSearch={recordSearch} />
  if (section === 'feedback-quality') return <FeedbackQualityLivePage recordSearch={recordSearch} />
  if (section === 'reports-analytics') return <ReportsAnalyticsLivePage />
  if (section === 'real-estate-inventory')
    return <RealEstateInventoryLivePage recordSearch={recordSearch} />
  if (section === 'survey-engineering-others')
    return <SpecializedOperationsLivePage recordSearch={recordSearch} />

  if (serviceAdministrationSections.has(section as ServiceAdministrationSection)) {
    return (
      <ServiceAdministrationSectionPage
        section={section as ServiceAdministrationSection}
        recordSearch={recordSearch}
      />
    )
  }

  const title = formatSectionTitle(section)

  return (
    <ModuleShellPage
      eyebrow="Service Operations"
      title={title}
      description="This Service Operations section is not available."
      backTo="/app/dashboard"
      backLabel="Back to dashboard"
    />
  )
}
