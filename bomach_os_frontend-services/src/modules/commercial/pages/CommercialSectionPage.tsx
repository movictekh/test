import { IconFilePlus, IconPlus } from '@tabler/icons-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useMemo, useState } from 'react'

import {
  CompactPageToolbar,
  CompactActionButton,
  ModulePageFrame,
  ModulePageStatus,
} from '@/shared/ui/module-controls'
import { presentError } from '@/shared/errors'
import { serviceAdministrationQueries } from '@/modules/service-administration/api/service-administration.queries'
import { fulfillmentKeys } from '@/modules/fulfillment/api/fulfillment.keys'
import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'
import { canPerformAction } from '@/app/permissions'
import { useAuth } from '@/app/auth'
import { useDeepLinkedSelection, type AppRecordSearch } from '@/shared/navigation'

import { commercialApi, type UpdateServiceRequestInput } from '../api/commercial.api'
import { commercialKeys } from '../api/commercial.keys'
import { commercialQueries } from '../api/commercial.queries'
import { ServiceRequestsScreen } from '../screens/ServiceRequestsScreen'
import { QuotationsScreen } from '../screens/QuotationsScreen'
import { InvoicesPaymentsScreen } from '../screens/InvoicesPaymentsScreen'
import { ApprovalsScreen } from '../screens/ApprovalsScreen'
import type {
  CommercialSection,
  CommercialServiceRequest,
  CreateInvoiceInput,
  RecordPaymentInput,
  DecideApprovalInput,
  CreateQuotationInput,
  CreateServiceRequestInput,
  UpdateQuotationInput,
} from '../types/commercial.types'
import { CreateRequestWorkspace } from '../workspaces/CreateRequestWorkspace'
import { Request360Workspace } from '../workspaces/Request360Workspace'
import { QuotationBuilderWorkspace } from '../workspaces/QuotationBuilderWorkspace'
import { QuotationDetailWorkspace } from '../workspaces/QuotationDetailWorkspace'
import { InvoiceBuilderWorkspace } from '../workspaces/InvoiceBuilderWorkspace'
import { InvoiceDetailWorkspace } from '../workspaces/InvoiceDetailWorkspace'
import { ApprovalDecisionWorkspace } from '../workspaces/ApprovalDecisionWorkspace'
import '../styles/commercial.css'

const metadata: Record<CommercialSection, { title: string; breadcrumb: string }> = {
  'service-requests': { title: 'Service Requests', breadcrumb: 'Commercial flow / Requests' },
  quotations: { title: 'Quotations & Proposals', breadcrumb: 'Commercial flow / Offers' },
  'invoices-payments': {
    title: 'Invoices & Payments',
    breadcrumb: 'Commercial flow / Billing',
  },
  approvals: { title: 'Approvals', breadcrumb: 'Commercial flow / Approvals' },
}

export function CommercialSectionPage({
  section,
  recordSearch,
}: {
  section: CommercialSection
  recordSearch?: AppRecordSearch
}) {
  const navigate = useNavigate()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const toast = useToast()
  const query = useQuery(commercialQueries.workspace())
  const serviceAdministrationQuery = useQuery(serviceAdministrationQueries.workspace())
  const [createOpen, setCreateOpen] = useState(false)
  const [selectedRequestId, setSelectedRequestId] = useDeepLinkedSelection(recordSearch?.request)
  const [quotationBuilderOpen, setQuotationBuilderOpen] = useState(false)
  const [quotationSourceRequestId, setQuotationSourceRequestId] = useState<string | undefined>()
  const [selectedQuotationId, setSelectedQuotationId] = useDeepLinkedSelection(
    recordSearch?.quotation,
  )
  const [invoiceBuilderOpen, setInvoiceBuilderOpen] = useState(false)
  const [invoiceSourceQuotationId, setInvoiceSourceQuotationId] = useState<string | undefined>()
  const [selectedInvoiceId, setSelectedInvoiceId] = useDeepLinkedSelection(recordSearch?.invoice)
  const [selectedApprovalId, setSelectedApprovalId] = useDeepLinkedSelection(recordSearch?.approval)

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

  const createQuotation = useMutation({
    mutationFn: (input: CreateQuotationInput) => commercialApi.createQuotation(input),
    onSuccess: (workspace, input) => {
      queryClient.setQueryData(commercialKeys.workspace(), workspace)
      setQuotationBuilderOpen(false)
      setQuotationSourceRequestId(undefined)
      toast.success(
        input.status === 'Awaiting Approval'
          ? 'Quotation submitted for approval'
          : 'Quotation draft saved',
      )
    },
    onError: (error) => {
      const e = presentError(error, 'form-submit')
      toast.error('Quotation could not be saved', { description: e.message })
    },
  })

  const updateQuotation = useMutation({
    mutationFn: ({ quotationId, input }: { quotationId: string; input: UpdateQuotationInput }) =>
      commercialApi.updateQuotation(quotationId, input),
    onSuccess: (workspace) => {
      queryClient.setQueryData(commercialKeys.workspace(), workspace)
      toast.success('Quotation updated')
    },
    onError: (error) => {
      const e = presentError(error, 'background-action')
      toast.error('Quotation could not be updated', { description: e.message })
    },
  })

  const createInvoice = useMutation({
    mutationFn: (input: CreateInvoiceInput) => commercialApi.createInvoice(input),
    onSuccess: (workspace) => {
      queryClient.setQueryData(commercialKeys.workspace(), workspace)
      setInvoiceBuilderOpen(false)
      setInvoiceSourceQuotationId(undefined)
      toast.success('Invoice created')
    },
    onError: (error) => {
      const e = presentError(error, 'form-submit')
      toast.error('Invoice could not be created', {
        description: e.message,
      })
    },
  })

  const recordPayment = useMutation({
    mutationFn: (input: RecordPaymentInput) => commercialApi.recordPayment(input),
    onSuccess: (workspace) => {
      queryClient.setQueryData(commercialKeys.workspace(), workspace)
      void queryClient.invalidateQueries({ queryKey: fulfillmentKeys.workspace() })
      toast.success('Payment recorded')
    },
    onError: (error) => {
      const e = presentError(error, 'form-submit')
      toast.error('Payment could not be recorded', {
        description: e.message,
      })
    },
  })

  const decideApproval = useMutation({
    mutationFn: (input: DecideApprovalInput) => commercialApi.decideApproval(input),
    onSuccess: (workspace) => {
      queryClient.setQueryData(commercialKeys.workspace(), workspace)
      setSelectedApprovalId(null)
      toast.success('Approval decision recorded')
    },
    onError: (error) => {
      const e = presentError(error, 'background-action')
      toast.error('Approval could not be updated', {
        description: e.message,
      })
    },
  })

  const updateRequest = useMutation({
    mutationFn: ({ requestId, input }: { requestId: string; input: UpdateServiceRequestInput }) =>
      commercialApi.updateRequest(requestId, input),
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

  const selectedQuotation = useMemo(() => {
    if (!selectedQuotationId || !query.data) return null
    return query.data.quotations.find((item) => item.id === selectedQuotationId) ?? null
  }, [query.data, selectedQuotationId])

  const selectedInvoice = useMemo(() => {
    if (!selectedInvoiceId || !query.data) return null
    return query.data.invoices.find((item) => item.id === selectedInvoiceId) ?? null
  }, [query.data, selectedInvoiceId])

  const selectedApproval = useMemo(() => {
    if (!selectedApprovalId || !query.data) return null
    return query.data.approvals.find((item) => item.id === selectedApprovalId) ?? null
  }, [query.data, selectedApprovalId])

  if (query.isPending || serviceAdministrationQuery.isPending) {
    return (
      <ModulePageStatus title={metadata[section].title} breadcrumb={metadata[section].breadcrumb}>
        <DashboardSkeleton />
      </ModulePageStatus>
    )
  }
  if (query.isError || serviceAdministrationQuery.isError) {
    const sourceError = query.error ?? serviceAdministrationQuery.error
    const e = presentError(sourceError, 'page-load')
    return (
      <ModulePageStatus title={metadata[section].title} breadcrumb={metadata[section].breadcrumb}>
        <ErrorState
          title={e.title}
          description={e.message}
          onRetry={() => {
            void query.refetch()
            void serviceAdministrationQuery.refetch()
          }}
        />
      </ModulePageStatus>
    )
  }

  const page = metadata[section]
  const canCreatePrimary =
    section === 'service-requests' || section === 'approvals'
      ? canPerformAction(user, 'requestCreate')
      : section === 'quotations'
        ? canPerformAction(user, 'quoteCreate')
        : canPerformAction(user, 'invoiceCreate')

  const canConfirmPayment = canPerformAction(user, 'paymentsCreate')
  const canApproveApproval = canPerformAction(user, 'approvalRequestsApprove')
  const canRejectApproval = canPerformAction(user, 'approvalRequestsReject')

  return (
    <>
      <ModulePageFrame
        header={
          <CompactPageToolbar
            title={page.title}
            breadcrumb={page.breadcrumb}
            primaryAction={
              <CompactActionButton
                tone="primary"
                disabled={!canCreatePrimary}
                locked={!canCreatePrimary}
                onClick={() => {
                  if (!canCreatePrimary) return
                  if (section === 'service-requests' || section === 'approvals') {
                    if (section === 'approvals') {
                      void navigate({
                        to: '/app/$section',
                        params: { section: 'service-requests' },
                      })
                    }
                    setCreateOpen(true)
                    return
                  }
                  if (section === 'quotations') setQuotationBuilderOpen(true)
                  if (section === 'invoices-payments') setInvoiceBuilderOpen(true)
                }}
              >
                {section === 'service-requests' || section === 'approvals' ? (
                  <IconFilePlus size={14} />
                ) : (
                  <IconPlus size={14} />
                )}{' '}
                {section === 'service-requests' || section === 'approvals'
                  ? 'New Request'
                  : section === 'quotations'
                    ? 'Build Quote'
                    : section === 'invoices-payments'
                      ? 'New Invoice'
                      : 'Create'}
              </CompactActionButton>
            }
          />
        }
      >
        {section === 'service-requests' ? (
          <ServiceRequestsScreen
            summary={query.data.summary}
            requests={query.data.requests}
            onOpenRequest={(request: CommercialServiceRequest) => setSelectedRequestId(request.id)}
          />
        ) : section === 'quotations' ? (
          <QuotationsScreen
            summary={query.data.quotationSummary}
            quotations={query.data.quotations}
            onOpen={(quotation) => setSelectedQuotationId(quotation.id)}
          />
        ) : section === 'invoices-payments' ? (
          <InvoicesPaymentsScreen
            summary={query.data.invoiceSummary}
            invoices={query.data.invoices}
            onOpen={(invoice) => setSelectedInvoiceId(invoice.id)}
          />
        ) : section === 'approvals' ? (
          <ApprovalsScreen
            summary={query.data.approvalSummary}
            approvals={query.data.approvals}
            onOpen={(approval) => setSelectedApprovalId(approval.id)}
          />
        ) : null}

        {createOpen ? (
          <CreateRequestWorkspace
            saving={createRequest.isPending}
            serviceWorkspace={serviceAdministrationQuery.data}
            onClose={() => setCreateOpen(false)}
            onSubmit={(input) => createRequest.mutate(input)}
          />
        ) : null}

        {selectedRequest ? (
          <Request360Workspace
            key={selectedRequest.id}
            request={selectedRequest}
            saving={updateRequest.isPending}
            onClose={() => setSelectedRequestId(null)}
            onUpdate={(requestId, input) => updateRequest.mutate({ requestId, input })}
            onPrepareQuotation={(requestId) => {
              setSelectedRequestId(null)
              setQuotationSourceRequestId(requestId)
              setQuotationBuilderOpen(true)
              void navigate({
                to: '/app/$section',
                params: { section: 'quotations' },
              })
            }}
          />
        ) : null}

        {quotationBuilderOpen ? (
          <QuotationBuilderWorkspace
            requests={query.data.requests}
            {...(quotationSourceRequestId ? { initialRequestId: quotationSourceRequestId } : {})}
            saving={createQuotation.isPending}
            onClose={() => {
              setQuotationBuilderOpen(false)
              setQuotationSourceRequestId(undefined)
            }}
            onSubmit={(input) => createQuotation.mutate(input)}
          />
        ) : null}

        {selectedQuotation ? (
          <QuotationDetailWorkspace
            key={selectedQuotation.id}
            quotation={selectedQuotation}
            saving={updateQuotation.isPending}
            onClose={() => setSelectedQuotationId(null)}
            onUpdate={(quotationId, input) => updateQuotation.mutate({ quotationId, input })}
            onCreateInvoice={(quotationId) => {
              setSelectedQuotationId(null)
              setInvoiceSourceQuotationId(quotationId)
              setInvoiceBuilderOpen(true)
              void navigate({
                to: '/app/$section',
                params: { section: 'invoices-payments' },
              })
            }}
          />
        ) : null}

        {invoiceBuilderOpen ? (
          <InvoiceBuilderWorkspace
            quotations={query.data.quotations}
            invoices={query.data.invoices}
            {...(invoiceSourceQuotationId ? { initialQuotationId: invoiceSourceQuotationId } : {})}
            saving={createInvoice.isPending}
            onClose={() => {
              setInvoiceBuilderOpen(false)
              setInvoiceSourceQuotationId(undefined)
            }}
            onSubmit={(input) => createInvoice.mutate(input)}
          />
        ) : null}

        {selectedInvoice ? (
          <InvoiceDetailWorkspace
            key={selectedInvoice.id}
            invoice={selectedInvoice}
            saving={recordPayment.isPending}
            onClose={() => setSelectedInvoiceId(null)}
            canConfirmPayment={canConfirmPayment}
            onRecordPayment={(input) => recordPayment.mutate(input)}
          />
        ) : null}

        {selectedApproval ? (
          <ApprovalDecisionWorkspace
            key={selectedApproval.id}
            approval={selectedApproval}
            saving={decideApproval.isPending}
            onClose={() => setSelectedApprovalId(null)}
            canApprove={canApproveApproval}
            canReject={canRejectApproval}
            onDecide={(input) => decideApproval.mutate(input)}
          />
        ) : null}
      </ModulePageFrame>
    </>
  )
}
