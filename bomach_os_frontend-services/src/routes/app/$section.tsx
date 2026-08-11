import { createFileRoute } from '@tanstack/react-router'

import { findNavigationItemByPath, operationsNavigation } from '@/app/navigation'
import { PERMISSIONS, requireRoutePermission } from '@/app/permissions'
import type { AppRecordSearch } from '@/shared/navigation'
import {
  ServiceAdministrationSectionPage,
  type ServiceAdministrationSection,
} from '@/modules/service-administration'
import { ModuleShellPage } from '@/modules/foundation/pages/ModuleShellPage'
import {
  CommercialSectionPage,
  ServiceRequestsLivePage,
  QuotationsLivePage,
  InvoicesPaymentsLivePage,
  ApprovalsLivePage,
  type CommercialSection,
} from '@/modules/commercial'
import {
  DeliverablesLivePage,
  ExecutionTasksLivePage,
  FulfillmentSectionPage,
  ServiceOrdersLivePage,
  type FulfillmentSection,
} from '@/modules/fulfillment'
import {
  ExperienceIntelligenceSectionPage,
  type ExperienceIntelligenceSection,
} from '@/modules/experience-intelligence'
import {
  SpecializedServicesSectionPage,
  type SpecializedServicesSection,
} from '@/modules/specialized-services'

const commercialSections = new Set<CommercialSection>([
  'service-requests',
  'quotations',
  'invoices-payments',
  'approvals',
])

const serviceAdministrationSections = new Set<ServiceAdministrationSection>([
  'service-catalogue',
  'calculator-library',
  'request-form-builder',
  'workflow-designer',
  'branch-activation',
])

const fulfillmentSections = new Set<FulfillmentSection>([
  'service-orders',
  'execution-tasks',
  'deliverables',
])

const specializedSections = new Set<SpecializedServicesSection>([
  'real-estate-inventory',
  'survey-engineering-others',
])

const experienceIntelligenceSections = new Set<ExperienceIntelligenceSection>([
  'feedback-quality',
  'reports-analytics',
  'audit-log',
])

export type AppSectionSearch = AppRecordSearch & {
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
  page?: number
}

export function parseRecordSearch(search: Record<string, unknown>): AppSectionSearch {
  const stringValue = (value: unknown): string | undefined =>
    typeof value === 'string' && value.trim() ? value : undefined

  const result: AppSectionSearch = {}
  const request = stringValue(search.request)
  const quotation = stringValue(search.quotation)
  const invoice = stringValue(search.invoice)
  const approval = stringValue(search.approval)
  const order = stringValue(search.order)
  const task = stringValue(search.task)
  const deliverable = stringValue(search.deliverable)
  const feedback = stringValue(search.feedback)

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
  const requestService = stringValue(search.service)
  const deliverableType = stringValue(search.deliverableType)
  const clientVisible = stringValue(search.clientVisible)
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
  if (feedback) result.feedback = feedback

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
    })
  },
  component: AppShellRoute,
})

function AppShellRoute() {
  const { section } = Route.useParams()
  const recordSearch = Route.useSearch()

  if (section === 'service-requests') return <ServiceRequestsLivePage recordSearch={recordSearch} />
  if (section === 'quotations') return <QuotationsLivePage recordSearch={recordSearch} />
  if (section === 'invoices-payments') return <InvoicesPaymentsLivePage recordSearch={recordSearch} />
  if (section === 'approvals') return <ApprovalsLivePage recordSearch={recordSearch} />
  if (section === 'service-orders') return <ServiceOrdersLivePage recordSearch={recordSearch} />
  if (section === 'execution-tasks') return <ExecutionTasksLivePage recordSearch={recordSearch} />
  if (section === 'deliverables') return <DeliverablesLivePage recordSearch={recordSearch} />

  if (commercialSections.has(section as CommercialSection)) {
    return <CommercialSectionPage section={section as CommercialSection} recordSearch={recordSearch} />
  }

  if (serviceAdministrationSections.has(section as ServiceAdministrationSection)) {
    return <ServiceAdministrationSectionPage section={section as ServiceAdministrationSection} recordSearch={recordSearch} />
  }

  if (fulfillmentSections.has(section as FulfillmentSection)) {
    return <FulfillmentSectionPage section={section as FulfillmentSection} recordSearch={recordSearch} />
  }

  if (specializedSections.has(section as SpecializedServicesSection)) {
    return <SpecializedServicesSectionPage section={section as SpecializedServicesSection} />
  }

  if (experienceIntelligenceSections.has(section as ExperienceIntelligenceSection)) {
    return <ExperienceIntelligenceSectionPage section={section as ExperienceIntelligenceSection} recordSearch={recordSearch} />
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
