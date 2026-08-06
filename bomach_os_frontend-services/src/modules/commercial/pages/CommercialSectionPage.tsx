import { IconFilePlus, IconPlus, IconUserScreen } from '@tabler/icons-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import {
  CompactPageToolbar,
  PrototypeButton,
} from '@/modules/service-administration/components/ServiceAdministrationUi'
import { presentError } from '@/shared/errors'
import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'
import { commercialApi } from '../api/commercial.api'
import { commercialKeys } from '../api/commercial.keys'
import { commercialQueries } from '../api/commercial.queries'
import { ServiceRequestsScreen } from '../screens/ServiceRequestsScreen'
import type {
  CommercialSection,
  CommercialServiceRequest,
  CreateServiceRequestInput,
} from '../types/commercial.types'
import { CreateRequestWorkspace } from '../workspaces/CreateRequestWorkspace'
import { Request360Workspace } from '../workspaces/Request360Workspace'
import '../styles/commercial.css'
const metadata: Record<CommercialSection, { title: string; breadcrumb: string }> = {
  'service-requests': { title: 'Service Requests', breadcrumb: 'Commercial flow / Requests' },
  quotations: { title: 'Quotations', breadcrumb: 'Commercial flow / Offers' },
  'invoices-payments': { title: 'Invoices & Payments', breadcrumb: 'Commercial flow / Billing' },
  approvals: { title: 'Approvals', breadcrumb: 'Commercial flow / Approvals' },
}
export function CommercialSectionPage({ section }: { section: CommercialSection }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()
  const query = useQuery(commercialQueries.workspace())
  const [createOpen, setCreateOpen] = useState(false)
  const [selectedRequest, setSelectedRequest] = useState<CommercialServiceRequest | null>(null)
  const createRequest = useMutation({
    mutationFn: (input: CreateServiceRequestInput) => commercialApi.createRequest(input),
    onSuccess: (workspace, input) => {
      queryClient.setQueryData(commercialKeys.workspace(), workspace)
      setCreateOpen(false)
      toast.success(input.submit ? 'Request submitted' : 'Request draft saved')
    },
    onError: (error) => {
      const e = presentError(error, 'form-submit')
      toast.error('Request could not be saved', { description: e.message })
    },
  })
  if (query.isPending) return <DashboardSkeleton />
  if (query.isError) {
    const e = presentError(query.error, 'page-load')
    return (
      <ErrorState title={e.title} description={e.message} onRetry={() => void query.refetch()} />
    )
  }
  const page = metadata[section]
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
          <PrototypeButton
            tone="primary"
            onClick={() => section === 'service-requests' && setCreateOpen(true)}
          >
            {section === 'service-requests' ? <IconFilePlus size={14} /> : <IconPlus size={14} />}{' '}
            {section === 'service-requests' ? 'New Request' : 'Create'}
          </PrototypeButton>
        }
      />
      {section === 'service-requests' ? (
        <ServiceRequestsScreen
          summary={query.data.summary}
          requests={query.data.requests}
          onOpenRequest={setSelectedRequest}
        />
      ) : (
        <main className="commercial-content">
          <section className="commercial-card commercial-empty">
            This exact prototype screen is implemented in the next Phase UI-2 slice.
          </section>
        </main>
      )}
      <CreateRequestWorkspace
        open={createOpen}
        saving={createRequest.isPending}
        onClose={() => setCreateOpen(false)}
        onSubmit={(x) => createRequest.mutate(x)}
      />
      {selectedRequest ? (
        <Request360Workspace request={selectedRequest} onClose={() => setSelectedRequest(null)} />
      ) : null}
    </>
  )
}
