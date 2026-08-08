import { IconFilePlus, IconPlus } from '@tabler/icons-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useState } from 'react'

import { useAuth } from '@/app/auth'

import { CalculatorEditor, RequestFormEditor } from '../editors/ServiceAdministrationEditors'
import {
  ConfigureServiceWorkspace,
  CreateServiceWizard,
} from '../workspaces/ServiceCatalogueWorkspaces'

import { presentError } from '@/shared/errors'
import { ApiError } from '@/shared/api/api-error'
import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'
import {
  AccessLockIcon,
  CompactPageToolbar,
  CompactActionButton,
  ModulePageFrame,
  ModulePageStatus,
} from '@/shared/ui/module-controls'

import { serviceAdministrationBackendApi } from '../api/service-administration.backend-api'
import { serviceAdministrationKeys } from '../api/service-administration.keys'
import {
  createServiceThroughRequestForm,
  publishLiveService,
  saveLivePricingConfig,
  saveLiveRequestForm,
  saveLiveWorkflow,
  ServiceSetupStageError,
} from '../api/service-administration.live-mutations'
import { serviceAdministrationQueries } from '../api/service-administration.queries'
import { BranchActivationScreen } from '../screens/BranchActivationScreen'
import {
  CalculatorLibraryScreen,
  RequestFormBuilderScreen,
  ServiceCatalogueScreen,
} from '../screens/ServiceAdministrationScreens'
import { WorkflowDesignerScreen } from '../screens/WorkflowDesignerScreen'
import { getServiceAdministrationCapabilities } from '../permissions'
import type {
  ConfigureServiceInput,
  CreateServiceWizardInput,
  PricingCalculator,
  ServiceCatalogueItem,
  ServiceRequestForm,
  ServiceWorkflow,
  SaveBranchActivationMatrixInput,
  SaveCalculatorInput,
  SaveRequestFormInput,
  SaveWorkflowInput,
} from '../types/service-administration.types'

export type ServiceAdministrationSection =
  | 'service-catalogue'
  | 'calculator-library'
  | 'request-form-builder'
  | 'workflow-designer'
  | 'branch-activation'

const metadata: Record<
  ServiceAdministrationSection,
  { title: string; breadcrumb: string; description: string }
> = {
  'service-catalogue': {
    title: 'Service Catalogue',
    breadcrumb: 'Services / Setup and activation',
    description: 'Configure the services Bomach can sell and fulfil.',
  },
  'calculator-library': {
    title: 'Calculator Library',
    breadcrumb: 'Services / Pricing engine',
    description: 'Create and manage reusable service pricing calculators.',
  },
  'request-form-builder': {
    title: 'Request Form Builder',
    breadcrumb: 'Services / Form design',
    description: 'Design the intake fields used for each service request.',
  },
  'workflow-designer': {
    title: 'Workflow Designer',
    breadcrumb: 'Services / Fulfillment automation',
    description: 'Define fulfilment stages, ownership, SLA and controls.',
  },
  'branch-activation': {
    title: 'Branch Activation',
    breadcrumb: 'Services / Availability and capacity',
    description: 'Control where each service can be offered and delivered.',
  },
}

export interface ServiceAdministrationRecordSearch {
  search?: string
  status?: string
  division?: string
  page?: number
}

export function ServiceAdministrationSectionPage({
  section,
  recordSearch = {},
}: {
  section: ServiceAdministrationSection
  recordSearch?: ServiceAdministrationRecordSearch
}) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { user } = useAuth()
  const toast = useToast()
  const capabilities = getServiceAdministrationCapabilities(user)
  const catalogueSearch = section === 'service-catalogue' ? (recordSearch.search ?? '') : ''
  const catalogueDivision = section === 'service-catalogue' ? (recordSearch.division ?? '') : ''
  const catalogueStatus = section === 'service-catalogue' ? (recordSearch.status ?? '') : ''
  const cataloguePage = section === 'service-catalogue' ? Math.max(1, recordSearch.page ?? 1) : 1
  const cataloguePageSize = 12
  const usesLiveCatalogue =
    section === 'service-catalogue' ||
    section === 'request-form-builder' ||
    section === 'calculator-library' ||
    section === 'workflow-designer'

  const workspaceQuery = useQuery({
    ...serviceAdministrationQueries.workspace(),
    enabled: !usesLiveCatalogue,
  })
  const catalogueQuery = useQuery({
    ...serviceAdministrationQueries.catalogueList({
      ...(section === 'service-catalogue' && catalogueSearch ? { search: catalogueSearch } : {}),
      ...(section === 'service-catalogue' && catalogueDivision
        ? { division: catalogueDivision }
        : {}),
      ...(section === 'service-catalogue' && catalogueStatus ? { status: catalogueStatus } : {}),
      limit: section === 'service-catalogue' ? cataloguePageSize : 100,
      offset: section === 'service-catalogue' ? (cataloguePage - 1) * cataloguePageSize : 0,
    }),
    enabled: usesLiveCatalogue,
    placeholderData: (previousData) => previousData,
  })
  const categoryQuery = useQuery({
    ...serviceAdministrationQueries.categories(),
    enabled: capabilities.canCreateInitialServiceSetup,
  })
  const fieldTypesQuery = useQuery({
    ...serviceAdministrationQueries.requestFieldTypes(),
    enabled: section === 'request-form-builder' && capabilities.canListRequestForms,
  })
  const pricingQuery = useQuery({
    ...serviceAdministrationQueries.pricingConfigs(capabilities.canViewPricingConfig),
    enabled: section === 'calculator-library' && capabilities.canListPricingConfigs,
  })
  const branchesQuery = useQuery({
    ...serviceAdministrationQueries.branches(),
    enabled:
      section === 'branch-activation' &&
      capabilities.canListBranches &&
      capabilities.canListBranchActivations,
  })
  const rolesQuery = useQuery({
    ...serviceAdministrationQueries.roles(),
    enabled: section === 'workflow-designer' && capabilities.canListRoles,
  })
  const branchMatrixQuery = useQuery({
    ...serviceAdministrationQueries.branchActivationMatrix(),
    enabled: section === 'branch-activation' && capabilities.canListBranchActivations,
  })
  const [selectedService, setSelectedService] = useState<ServiceCatalogueItem | null>(null)
  const [newServiceOpen, setNewServiceOpen] = useState(false)
  const [calculatorEditor, setCalculatorEditor] = useState<PricingCalculator | null | 'new'>(null)
  const [formEditor, setFormEditor] = useState<ServiceRequestForm | null | 'new'>(null)
  const [selectedRequestFormServiceId, setSelectedRequestFormServiceId] = useState('')
  const [selectedWorkflowServiceId, setSelectedWorkflowServiceId] = useState('')

  const workflowService =
    catalogueQuery.data?.items.find((item) => item.id === selectedWorkflowServiceId) ??
    catalogueQuery.data?.items[0]
  const workflowServiceId = Number(workflowService?.id ?? 0)
  const workflowsQuery = useQuery({
    ...serviceAdministrationQueries.workflows(
      workflowServiceId,
      workflowService?.name ?? 'Service',
    ),
    enabled:
      section === 'workflow-designer' && capabilities.canListWorkflows && workflowServiceId > 0,
  })

  const requestFormService =
    catalogueQuery.data?.items.find((item) => item.id === selectedRequestFormServiceId) ??
    catalogueQuery.data?.items[0]
  const requestFormServiceId = Number(requestFormService?.id ?? 0)
  const requestFormsQuery = useQuery({
    ...serviceAdministrationQueries.requestForms(
      requestFormServiceId,
      requestFormService?.name ?? 'Service',
    ),
    enabled:
      section === 'request-form-builder' &&
      capabilities.canListRequestForms &&
      Number.isFinite(requestFormServiceId) &&
      requestFormServiceId > 0,
  })

  const createService = useMutation({
    mutationFn: (input: CreateServiceWizardInput) => createServiceThroughRequestForm(input),
    onSuccess: async (service) => {
      await queryClient.invalidateQueries({ queryKey: serviceAdministrationKeys.catalogue() })
      setNewServiceOpen(false)
      toast.success('Initial Service setup created', {
        description: `${service.name} is saved as a draft with sub-services and a request form.`,
      })
    },
    onError: async (error) => {
      await queryClient.invalidateQueries({ queryKey: serviceAdministrationKeys.catalogue() })

      if (error instanceof ServiceSetupStageError && error.serviceId) {
        toast.error('Service draft needs attention', {
          description: error.message,
        })
        return
      }

      const presented = presentError(error, 'background-action')
      toast.error('Service could not be created', {
        description: presented.message,
      })
    },
  })

  const saveCalculator = useMutation({
    mutationFn: (input: SaveCalculatorInput) => saveLivePricingConfig(input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: serviceAdministrationKeys.pricingConfigs({}),
      })
      await queryClient.invalidateQueries({ queryKey: serviceAdministrationKeys.catalogue() })
      setCalculatorEditor(null)
      toast.success('Calculator saved')
    },
    onError: (error) => {
      const presented = presentError(error, 'background-action')
      const description =
        error instanceof Error && !(error instanceof ApiError) ? error.message : presented.message
      toast.error('Calculator could not be saved', { description })
    },
  })

  const saveRequestForm = useMutation({
    mutationFn: async (input: SaveRequestFormInput) => {
      const service = catalogueQuery.data?.items.find((item) => item.id === input.serviceId)
      return saveLiveRequestForm(input, service?.name ?? 'Service')
    },
    onSuccess: async (form) => {
      await queryClient.invalidateQueries({
        queryKey: serviceAdministrationKeys.requestForms(Number(form.serviceId)),
      })
      await queryClient.invalidateQueries({ queryKey: serviceAdministrationKeys.catalogue() })
      setSelectedRequestFormServiceId(form.serviceId)
      setFormEditor(null)
      toast.success('Request form saved')
    },
    onError: (error) => {
      const presented = presentError(error, 'background-action')
      toast.error('Request form could not be saved', {
        description: presented.message,
      })
    },
  })

  const saveWorkflow = useMutation({
    mutationFn: (input: SaveWorkflowInput) => {
      const service = catalogueQuery.data?.items.find((item) => item.id === input.serviceId)
      return saveLiveWorkflow(input, service?.name ?? 'Service')
    },
    onSuccess: async (workflow) => {
      await queryClient.invalidateQueries({
        queryKey: serviceAdministrationKeys.workflows(Number(workflow.serviceId)),
      })
      await queryClient.invalidateQueries({ queryKey: serviceAdministrationKeys.catalogue() })
      toast.success('Workflow saved')
    },
    onError: (error) => {
      const presented = presentError(error, 'background-action')
      toast.error('Workflow could not be saved', { description: presented.message })
    },
  })

  const saveBranchActivationMatrix = useMutation({
    mutationFn: async (input: SaveBranchActivationMatrixInput) => {
      const byService = new Map<string, typeof input.updates>()
      for (const update of input.updates) {
        const current = byService.get(update.serviceId) ?? []
        current.push(update)
        byService.set(update.serviceId, current)
      }

      await Promise.all(
        [...byService.entries()].map(([serviceId, updates]) =>
          serviceAdministrationBackendApi.upsertBranchActivations(
            Number(serviceId),
            updates.map((update) => ({
              branch_id: Number(update.branchId),
              status: update.active ? 'active' : 'inactive',
              client_visible: update.clientVisible,
              capacity: update.capacity,
              activated_at: update.activatedAt,
            })),
          ),
        ),
      )
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: serviceAdministrationKeys.branchActivationMatrix({}),
      })
      await queryClient.invalidateQueries({ queryKey: serviceAdministrationKeys.catalogue() })
      toast.success('Branch settings saved')
    },
    onError: (error) => {
      const presented = presentError(error, 'background-action')
      toast.error('Branch settings could not be saved', { description: presented.message })
    },
  })

  const publishService = useMutation({
    mutationFn: (serviceId: number) => publishLiveService(serviceId),
    onSuccess: async (service) => {
      await queryClient.invalidateQueries({ queryKey: serviceAdministrationKeys.catalogue() })
      setSelectedService(service)
      toast.success('Service published successfully')
    },
    onError: (error) => {
      const presented = presentError(error, 'background-action')
      toast.error('Service could not be published', { description: presented.message })
    },
  })

  const activeQuery =
    section === 'service-catalogue' ||
    section === 'request-form-builder' ||
    section === 'workflow-designer'
      ? catalogueQuery
      : section === 'calculator-library'
        ? pricingQuery
        : section === 'branch-activation'
          ? branchMatrixQuery
          : workspaceQuery

  if (activeQuery.isLoading)
    return (
      <ModulePageStatus title={metadata[section].title} breadcrumb={metadata[section].breadcrumb}>
        <DashboardSkeleton />
      </ModulePageStatus>
    )
  if (activeQuery.isError) {
    const error = presentError(activeQuery.error, 'page-load')
    return (
      <ModulePageStatus title={metadata[section].title} breadcrumb={metadata[section].breadcrumb}>
        <ErrorState
          title={error.title}
          description={error.message}
          onRetry={() => void activeQuery.refetch()}
        />
      </ModulePageStatus>
    )
  }

  if (
    section === 'request-form-builder' &&
    requestFormService &&
    (requestFormsQuery.isPending || fieldTypesQuery.isPending)
  ) {
    return (
      <ModulePageStatus title={metadata[section].title} breadcrumb={metadata[section].breadcrumb}>
        <DashboardSkeleton />
      </ModulePageStatus>
    )
  }

  if (section === 'request-form-builder' && requestFormsQuery.isError) {
    const error = presentError(requestFormsQuery.error, 'page-load')
    return (
      <ModulePageStatus title={metadata[section].title} breadcrumb={metadata[section].breadcrumb}>
        <ErrorState
          title={error.title}
          description={error.message}
          onRetry={() => void requestFormsQuery.refetch()}
        />
      </ModulePageStatus>
    )
  }

  if (section === 'request-form-builder' && fieldTypesQuery.isError) {
    const error = presentError(fieldTypesQuery.error, 'page-load')
    return (
      <ModulePageStatus title={metadata[section].title} breadcrumb={metadata[section].breadcrumb}>
        <ErrorState
          title={error.title}
          description={error.message}
          onRetry={() => void fieldTypesQuery.refetch()}
        />
      </ModulePageStatus>
    )
  }

  const workspace = workspaceQuery.data
  const catalogue = catalogueQuery.data
  const page = metadata[section]
  const selectedCalculator = workspace?.calculators.find(
    (item) => item.serviceId === selectedService?.id,
  )
  const selectedRequestForm = workspace?.requestForms.find(
    (item) => item.serviceId === selectedService?.id,
  )
  const selectedWorkflow = workspace?.workflows.find(
    (item) => item.serviceId === selectedService?.id,
  )

  const openLiveServiceDetail = async (service: ServiceCatalogueItem) => {
    try {
      const serviceId = Number(service.id)

      if (!Number.isFinite(serviceId)) {
        throw new Error('The selected service has an invalid backend identifier.')
      }

      const detail = await queryClient.fetchQuery(
        serviceAdministrationQueries.catalogueDetail(serviceId),
      )
      setSelectedService(detail)
    } catch (error) {
      const presented = presentError(error, 'page-load')
      toast.error('Service details could not be loaded', {
        description: presented.message,
      })
    }
  }

  return (
    <>
      <ModulePageFrame
        header={
          <CompactPageToolbar
            title={page.title}
            breadcrumb={page.breadcrumb}
            secondaryAction={
              <CompactActionButton
                disabled={!capabilities.canCreateServiceRequest}
                locked={!capabilities.canCreateServiceRequest}
                onClick={() =>
                  void navigate({
                    to: '/app/$section',
                    params: { section: 'service-requests' },
                  })
                }
              >
                <IconFilePlus size={14} />
                New Request
              </CompactActionButton>
            }
            primaryAction={
              <CompactActionButton
                tone="primary"
                disabled={!capabilities.canCreateInitialServiceSetup}
                locked={!capabilities.canCreateInitialServiceSetup}
                onClick={() => setNewServiceOpen(true)}
              >
                <IconPlus size={14} />
                Create Service
              </CompactActionButton>
            }
          />
        }
      >
        {section === 'service-catalogue' ? (
          <ServiceCatalogueScreen
            services={catalogue?.items ?? []}
            totalCount={catalogue?.count ?? 0}
            query={catalogueSearch}
            division={catalogueDivision}
            status={catalogueStatus}
            page={cataloguePage}
            pageSize={cataloguePageSize}
            onFiltersChange={(filters) => {
              void navigate({
                to: '/app/$section',
                params: { section: 'service-catalogue' },
                search: (previous) => {
                  const next = { ...previous }
                  delete next.search
                  delete next.division
                  delete next.status
                  delete next.page

                  return {
                    ...next,
                    ...(filters.query ? { search: filters.query } : {}),
                    ...(filters.division ? { division: filters.division } : {}),
                    ...(filters.status ? { status: filters.status } : {}),
                  }
                },
                replace: true,
              })
            }}
            onPageChange={(nextPage) => {
              void navigate({
                to: '/app/$section',
                params: { section: 'service-catalogue' },
                search: (previous) => {
                  const next = { ...previous }
                  delete next.page

                  return {
                    ...next,
                    ...(nextPage > 1 ? { page: nextPage } : {}),
                  }
                },
                replace: true,
              })
            }}
            onConfigure={
              capabilities.canViewService
                ? (service) => void openLiveServiceDetail(service)
                : undefined
            }
            configureLabel="View"
            onCreate={
              capabilities.canCreateInitialServiceSetup ? () => setNewServiceOpen(true) : undefined
            }
            createDisabled={!capabilities.canCreateInitialServiceSetup}
            onBranchAvailability={
              capabilities.canListBranchActivations
                ? () =>
                    void navigate({
                      to: '/app/$section',
                      params: { section: 'branch-activation' },
                    })
                : undefined
            }
            branchAvailabilityDisabled={!capabilities.canListBranchActivations}
          />
        ) : null}

        {section === 'calculator-library' ? (
          <CalculatorLibraryScreen
            calculators={pricingQuery.data ?? []}
            hasServices={(catalogue?.items.length ?? 0) > 0}
            onCreate={
              capabilities.canCreatePricingConfig ? () => setCalculatorEditor('new') : undefined
            }
            createDisabled={
              !capabilities.canCreatePricingConfig || (catalogue?.items.length ?? 0) === 0
            }
            createLocked={!capabilities.canCreatePricingConfig}
          />
        ) : null}

        {section === 'request-form-builder' ? (
          <RequestFormBuilderScreen
            services={catalogue?.items ?? []}
            selectedServiceId={requestFormService?.id ?? ''}
            onSelectedServiceChange={setSelectedRequestFormServiceId}
            form={requestFormsQuery.data?.[0] ?? null}
            fieldTypes={fieldTypesQuery.data ?? []}
            saving={saveRequestForm.isPending}
            {...((
              requestFormsQuery.data?.[0]
                ? capabilities.canUpdateRequestForm
                : capabilities.canCreateRequestForm
            )
              ? { onSave: (input: SaveRequestFormInput) => saveRequestForm.mutate(input) }
              : {})}
          />
        ) : null}

        {section === 'workflow-designer' ? (
          <WorkflowDesignerScreen
            services={catalogue?.items ?? []}
            workflows={workflowsQuery.data ?? []}
            selectedServiceId={workflowService?.id ?? ''}
            onSelectedServiceChange={setSelectedWorkflowServiceId}
            ownerRoles={rolesQuery.data ?? []}
            saving={saveWorkflow.isPending}
            {...((
              workflowsQuery.data?.[0]
                ? capabilities.canUpdateWorkflow
                : capabilities.canCreateWorkflow
            )
              ? { onSave: (input: SaveWorkflowInput) => saveWorkflow.mutate(input) }
              : {})}
          />
        ) : null}

        {section === 'branch-activation' ? (
          <BranchActivationScreen
            services={branchMatrixQuery.data?.services ?? []}
            branches={branchesQuery.data ?? []}
            activations={branchMatrixQuery.data?.activations ?? []}
            saving={saveBranchActivationMatrix.isPending}
            {...(capabilities.canUpdateBranchActivations
              ? {
                  onSave: (input: SaveBranchActivationMatrixInput) =>
                    saveBranchActivationMatrix.mutate(input),
                }
              : {})}
          />
        ) : null}

        {selectedService &&
        section === 'service-catalogue' &&
        selectedService.status !== 'active' ? (
          <div className="service-admin-page service-admin-content">
            <div className="service-admin-card">
              <div className="service-admin-card-header">
                <div>
                  <div className="service-admin-card-title">Publish readiness</div>
                  <div className="service-admin-card-subtitle">
                    Backend readiness: request form + pricing config + active branch.
                  </div>
                </div>
                <button
                  type="button"
                  className="service-admin-button service-admin-button-primary"
                  disabled={
                    !capabilities.canPublishService ||
                    selectedService.readiness < 100 ||
                    publishService.isPending
                  }
                  title={
                    !capabilities.canPublishService
                      ? 'You do not have permission to publish services'
                      : selectedService.readiness < 100
                        ? 'Complete request form, pricing, and branch activation before publishing'
                        : undefined
                  }
                  onClick={() => publishService.mutate(Number(selectedService.id))}
                >
                  <AccessLockIcon show={!capabilities.canPublishService} />
                  {publishService.isPending ? 'Publishing…' : 'Publish Service'}
                </button>
              </div>
              <div className="service-admin-notice service-admin-notice-blue">
                Readiness: {selectedService.readiness}%
              </div>
            </div>
          </div>
        ) : null}
      </ModulePageFrame>

      {selectedService
        ? (() => {
            const configureWorkspaceProps: {
              service: ServiceCatalogueItem
              pending: boolean
              onClose: () => void
              onSave?: (input: ConfigureServiceInput) => void
              readOnly?: boolean
              calculator?: PricingCalculator
              requestForm?: ServiceRequestForm
              workflow?: ServiceWorkflow
            } = {
              service: selectedService,
              pending: false,
              onClose: () => setSelectedService(null),
              readOnly: true,
            }

            if (selectedCalculator) {
              configureWorkspaceProps.calculator = selectedCalculator
            }

            if (selectedRequestForm) {
              configureWorkspaceProps.requestForm = selectedRequestForm
            }

            if (selectedWorkflow) {
              configureWorkspaceProps.workflow = selectedWorkflow
            }

            return <ConfigureServiceWorkspace {...configureWorkspaceProps} />
          })()
        : null}

      {calculatorEditor ? (
        <CalculatorEditor
          {...(calculatorEditor === 'new' ? {} : { calculator: calculatorEditor })}
          services={catalogue?.items ?? []}
          onClose={() => setCalculatorEditor(null)}
          onSave={(input) => saveCalculator.mutate(input)}
          saving={saveCalculator.isPending}
        />
      ) : null}

      {formEditor ? (
        <RequestFormEditor
          {...(formEditor === 'new' ? {} : { form: formEditor })}
          services={catalogue?.items ?? []}
          onClose={() => setFormEditor(null)}
          onSave={(input) => saveRequestForm.mutate(input)}
          saving={saveRequestForm.isPending}
        />
      ) : null}

      {capabilities.canCreateInitialServiceSetup ? (
        <CreateServiceWizard
          open={newServiceOpen}
          categories={categoryQuery.data ?? []}
          onClose={() => setNewServiceOpen(false)}
          pending={createService.isPending}
          onSubmit={(value) => createService.mutate(value)}
        />
      ) : null}
    </>
  )
}
