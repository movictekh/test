import { IconFilePlus, IconPlus, IconUserScreen } from '@tabler/icons-react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'

import {
  CompactPageToolbar,
  PrototypeButton,
} from '@/modules/service-administration/components/ServiceAdministrationUi'
import { presentError } from '@/shared/errors'
import { DashboardSkeleton, ErrorState } from '@/shared/ui'

import { commercialQueries } from '../api/commercial.queries'
import { ServiceRequestsScreen } from '../screens/ServiceRequestsScreen'
import type { CommercialSection } from '../types/commercial.types'
import '../styles/commercial.css'

const metadata: Record<CommercialSection, { title: string; breadcrumb: string }> = {
  'service-requests': {
    title: 'Service Requests',
    breadcrumb: 'Commercial flow / Requests',
  },
  quotations: {
    title: 'Quotations & Proposals',
    breadcrumb: 'Commercial flow / Offers',
  },
  'invoices-payments': {
    title: 'Invoices & Payments',
    breadcrumb: 'Commercial flow / Billing',
  },
  approvals: {
    title: 'Approval Queue',
    breadcrumb: 'Governance / Approvals',
  },
}

export function CommercialSectionPage({ section }: { section: CommercialSection }) {
  const navigate = useNavigate()
  const query = useQuery(commercialQueries.workspace())
  const page = metadata[section]

  if (query.isPending) return <DashboardSkeleton />
  if (query.isError) {
    const error = presentError(query.error, 'page-load')
    return (
      <ErrorState
        title={error.title}
        description={error.message}
        onRetry={() => void query.refetch()}
      />
    )
  }

  return (
    <>
      <CompactPageToolbar
        title={page.title}
        breadcrumb={page.breadcrumb}
        secondaryAction={
          <PrototypeButton onClick={() => void navigate({ to: '/portal/dashboard' })}>
            <IconUserScreen size={14} />
            Client Portal
          </PrototypeButton>
        }
        primaryAction={
          <PrototypeButton tone="primary">
            {section === 'service-requests' ? <IconFilePlus size={14} /> : <IconPlus size={14} />}
            {section === 'service-requests' ? 'New Request' : 'Create'}
          </PrototypeButton>
        }
      />

      {section === 'service-requests' ? (
        <ServiceRequestsScreen summary={query.data.summary} requests={query.data.requests} />
      ) : (
        <main className="commercial-content">
          <section className="commercial-card commercial-empty" role="status">
            This exact prototype screen is implemented in the next Phase UI-2 slice.
          </section>
        </main>
      )}
    </>
  )
}
