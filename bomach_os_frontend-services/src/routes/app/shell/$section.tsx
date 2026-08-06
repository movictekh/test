import { createFileRoute } from '@tanstack/react-router'

import { findNavigationItemByPath, operationsNavigation } from '@/app/navigation'
import { PERMISSIONS, requireRoutePermission } from '@/app/permissions'
import {
  ServiceAdministrationSectionPage,
  type ServiceAdministrationSection,
} from '@/modules/service-administration'
import { ModuleShellPage } from '@/modules/foundation/pages/ModuleShellPage'
import { CommercialSectionPage, type CommercialSection } from '@/modules/commercial'

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

function formatSectionTitle(section: string): string {
  return section
    .split('-')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export const Route = createFileRoute('/app/shell/$section')({
  beforeLoad: ({ context, location }) => {
    const matchingItem = findNavigationItemByPath(operationsNavigation, location.pathname)

    return requireRoutePermission({
      auth: context.auth,
      permissions: matchingItem?.permissions ?? [PERMISSIONS.dashboardRead],
    })
  },
  component: AppShellRoute,
})

function AppShellRoute() {
  const { section } = Route.useParams()

  if (commercialSections.has(section as CommercialSection)) {
    return <CommercialSectionPage section={section as CommercialSection} />
  }

  if (serviceAdministrationSections.has(section as ServiceAdministrationSection)) {
    return <ServiceAdministrationSectionPage section={section as ServiceAdministrationSection} />
  }

  const title = formatSectionTitle(section)

  return (
    <ModuleShellPage
      eyebrow="Service Operations"
      title={title}
      description="This section will be replaced during its prototype-first UI phase."
      backTo="/app/dashboard"
      backLabel="Back to dashboard"
    />
  )
}
