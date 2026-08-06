import { IconFilePlus, IconPlus, IconUserScreen } from '@tabler/icons-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useMemo, useState } from 'react'

import {
  CompactPageToolbar,
  PrototypeButton,
} from '@/modules/service-administration/components/ServiceAdministrationUi'
import { presentError } from '@/shared/errors'
import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'

import { commercialApi, type UpdateServiceRequestInput } from '../api/commercial.api'
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
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null)

  const createRequest = useMutation({
    mutationFn: (input: CreateServiceRequestInput) => commercialApi.createRequest(input),
    onSuccess: (workspace) => {
      queryClient.setQueryData(commercialKeys.workspace(), workspace)
      setCreateOpen(false)
      toast.success('Request submitted')
    },
    onError: (error) => {
      const e = presentError(error, 'form-submit')
      toast.error('Request could not be saved', { description: e.message })
    },
  })

  const updateRequest = useMutation({
    mutationFn: ({
      requestId,
      input,
    }: {
      requestId: string
      input: UpdateServiceRequestInput
    }) => commercialApi.updateRequest(requestId, input),
    onSuccess: (workspace, variables) => {
      queryClient.setQueryData(commercialKeys.workspace(), workspace)
      const next = workspace.requests.find((item) => item.id === variables.requestId)
      if (!next) setSelectedRequestId(null)
    },
    onError: (error) => {
      const e = presentError(error, 'background-action')
      toast.error('Request could not be updated', { description: e.message })
    },
  })

  const selectedRequest = useMemo(() => {
    if (!selectedRequestId || !query.data) return null
    return query.data.requests.find((item) => item.id === selectedRequestId) ?? null
  }, [query.data, selectedRequestId])

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
          onOpenRequest={(request: CommercialServiceRequest) => setSelectedRequestId(request.id)}
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
        onSubmit={(input) => createRequest.mutate(input)}
      />

      {selectedRequest ? (
        <Request360Workspace
          request={selectedRequest}
          saving={updateRequest.isPending}
          onClose={() => setSelectedRequestId(null)}
          onUpdate={(requestId, input) => updateRequest.mutate({ requestId, input })}
          onPrepareQuotation={(requestId) => {
            setSelectedRequestId(null)
            toast.success('Opening quotation builder', {
              description: `Quotation draft will use ${requestId}.`,
            })
            void navigate({
              to: '/app/$section',
              params: { section: 'quotations' },
            })
          }}
        />
      ) : null}
    </>
  )
}
