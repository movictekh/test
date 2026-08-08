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
import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'
import { CompactPageToolbar, CompactActionButton } from '@/shared/ui/module-controls'

import { serviceAdministrationApi } from '../api/service-administration.api'
import { serviceAdministrationKeys } from '../api/service-administration.keys'
import {
  createServiceThroughRequestForm,
  saveLiveRequestForm,
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

export function ServiceAdministrationSectionPage({
  section,
}: {
  section: ServiceAdministrationSection
}) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { user } = useAuth()
  const toast = useToast()
  const capabilities = getServiceAdministrationCapabilities(user)
  const usesLiveCatalogue = section === 'service-catalogue' || section === 'request-form-builder'

  const workspaceQuery = useQuery({
    ...serviceAdministrationQueries.workspace(),
    enabled: !usesLiveCatalogue,
  })
  const catalogueQuery = useQuery({
    ...serviceAdministrationQueries.catalogueList({ limit: 100, offset: 0 }),
    enabled: usesLiveCatalogue,
  })
  const categoryQuery = useQuery({
    ...serviceAdministrationQueries.categories(),
    enabled: section === 'service-catalogue' && capabilities.canCreateInitialServiceSetup,
  })
  const fieldTypesQuery = useQuery({
    ...serviceAdministrationQueries.requestFieldTypes(),
    enabled: section === 'request-form-builder' && capabilities.canListRequestForms,
  })
  const [selectedService, setSelectedService] = useState<ServiceCatalogueItem | null>(null)
  const [newServiceOpen, setNewServiceOpen] = useState(false)
  const [calculatorEditor, setCalculatorEditor] = useState<PricingCalculator | null | 'new'>(null)
  const [formEditor, setFormEditor] = useState<ServiceRequestForm | null | 'new'>(null)
  const [selectedRequestFormServiceId, setSelectedRequestFormServiceId] = useState('')

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

  const configureService = useMutation({
    mutationFn: (input: ConfigureServiceInput) => serviceAdministrationApi.configureService(input),
    onSuccess: (workspace) => {
      queryClient.setQueryData(serviceAdministrationKeys.workspace(), workspace)
      setSelectedService(null)
      toast.success('Service configuration saved')
    },
    onError: (error) => {
      const presented = presentError(error, 'background-action')
      toast.error('Service configuration could not be saved', {
        description: presented.message,
      })
    },
  })

  const saveCalculator = useMutation({
    mutationFn: (input: SaveCalculatorInput) => serviceAdministrationApi.saveCalculator(input),
    onSuccess: (workspace) => {
      queryClient.setQueryData(serviceAdministrationKeys.workspace(), workspace)
      setCalculatorEditor(null)
      toast.success('Calculator saved')
    },
    onError: (error) => {
      const presented = presentError(error, 'background-action')
      toast.error('Calculator could not be saved', {
        description: presented.message,
      })
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
    mutationFn: (input: SaveWorkflowInput) => serviceAdministrationApi.saveWorkflow(input),
    onSuccess: (workspace) => {
      queryClient.setQueryData(serviceAdministrationKeys.workspace(), workspace)
      toast.success('Workflow saved')
    },
    onError: (error) => {
      const presented = presentError(error, 'background-action')
      toast.error('Workflow could not be saved', {
        description: presented.message,
      })
    },
  })

  const saveBranchActivationMatrix = useMutation({
    mutationFn: (input: SaveBranchActivationMatrixInput) =>
      serviceAdministrationApi.saveBranchActivationMatrix(input),
    onSuccess: (workspace) => {
      queryClient.setQueryData(serviceAdministrationKeys.workspace(), workspace)
      toast.success('Branch settings saved')
    },
    onError: (error) => {
      const presented = presentError(error, 'background-action')
      toast.error('Branch settings could not be saved', {
        description: presented.message,
      })
    },
  })

  const activeQuery = usesLiveCatalogue ? catalogueQuery : workspaceQuery

  if (activeQuery.isPending) return <DashboardSkeleton />
  if (activeQuery.isError) {
    const error = presentError(activeQuery.error, 'page-load')
    return (
      <ErrorState
        title={error.title}
        description={error.message}
        onRetry={() => void activeQuery.refetch()}
      />
    )
  }

  if (
    section === 'request-form-builder' &&
    requestFormService &&
    (requestFormsQuery.isPending || fieldTypesQuery.isPending)
  ) {
    return <DashboardSkeleton />
  }

  if (section === 'request-form-builder' && requestFormsQuery.isError) {
    const error = presentError(requestFormsQuery.error, 'page-load')
    return (
      <ErrorState
        title={error.title}
        description={error.message}
        onRetry={() => void requestFormsQuery.refetch()}
      />
    )
  }

  if (section === 'request-form-builder' && fieldTypesQuery.isError) {
    const error = presentError(fieldTypesQuery.error, 'page-load')
    return (
      <ErrorState
        title={error.title}
        description={error.message}
        onRetry={() => void fieldTypesQuery.refetch()}
      />
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
      <CompactPageToolbar
        title={page.title}
        breadcrumb={page.breadcrumb}
        secondaryAction={
          capabilities.canCreateServiceRequest ? (
            <CompactActionButton
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
          ) : undefined
        }
        primaryAction={
          section === 'service-catalogue' && capabilities.canCreateInitialServiceSetup ? (
            <CompactActionButton tone="primary" onClick={() => setNewServiceOpen(true)}>
              <IconPlus size={14} />
              Create Service
            </CompactActionButton>
          ) : section === 'request-form-builder' && capabilities.canCreateRequestForm ? (
            <CompactActionButton tone="primary" onClick={() => setFormEditor('new')}>
              <IconPlus size={14} />
              New Request Form
            </CompactActionButton>
          ) : undefined
        }
      />

      {section === 'service-catalogue' ? (
        <ServiceCatalogueScreen
          services={catalogue?.items ?? []}
          {...(capabilities.canViewService
            ? { onConfigure: (service) => void openLiveServiceDetail(service) }
            : {})}
          configureLabel="View"
          {...(capabilities.canCreateInitialServiceSetup
            ? { onCreate: () => setNewServiceOpen(true) }
            : {})}
          {...(capabilities.canListBranchActivations
            ? {
                onBranchAvailability: () =>
                  void navigate({
                    to: '/app/$section',
                    params: { section: 'branch-activation' },
                  }),
              }
            : {})}
        />
      ) : null}

      {section === 'calculator-library' ? (
        <CalculatorLibraryScreen
          calculators={workspace?.calculators ?? []}
          {...(capabilities.canCreatePricingConfig
            ? { onCreate: () => setCalculatorEditor('new') }
            : {})}
        />
      ) : null}

      {section === 'request-form-builder' ? (
        <>
          <div className="service-admin-page service-admin-content">
            <div className="service-admin-card">
              <div className="service-admin-card-header">
                <div>
                  <div className="service-admin-card-title">Service scope</div>
                  <div className="service-admin-card-subtitle">
                    Request forms are backend resources scoped to one Service.
                  </div>
                </div>
                <select
                  value={requestFormService?.id ?? ''}
                  onChange={(event) => setSelectedRequestFormServiceId(event.target.value)}
                >
                  {(catalogue?.items ?? []).map((service) => (
                    <option key={service.id} value={service.id}>
                      {service.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {requestFormsQuery.data?.length ? (
            <RequestFormBuilderScreen
              forms={requestFormsQuery.data}
              fieldTypes={fieldTypesQuery.data ?? []}
              {...(capabilities.canUpdateRequestForm
                ? { onSave: (input: SaveRequestFormInput) => saveRequestForm.mutate(input) }
                : {})}
            />
          ) : (
            <div className="service-admin-page service-admin-content">
              <div className="service-admin-card">
                <div className="service-admin-card-title">No request form yet</div>
                <div className="service-admin-card-subtitle">
                  Create the first request form for {requestFormService?.name ?? 'this service'}.
                </div>
              </div>
            </div>
          )}
        </>
      ) : null}

      {section === 'workflow-designer' ? (
        <WorkflowDesignerScreen
          services={workspace?.services ?? []}
          workflows={workspace?.workflows ?? []}
          saving={saveWorkflow.isPending}
          {...(capabilities.canUpdateWorkflow
            ? { onSave: (input: SaveWorkflowInput) => saveWorkflow.mutate(input) }
            : {})}
        />
      ) : null}

      {section === 'branch-activation' ? (
        <BranchActivationScreen
          services={workspace?.services ?? []}
          activations={workspace?.branchActivations ?? []}
          saving={saveBranchActivationMatrix.isPending}
          {...(capabilities.canUpdateBranchActivations
            ? {
                onSave: (input: SaveBranchActivationMatrixInput) =>
                  saveBranchActivationMatrix.mutate(input),
              }
            : {})}
        />
      ) : null}

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
              pending: configureService.isPending,
              onClose: () => setSelectedService(null),
              readOnly: section === 'service-catalogue' || !capabilities.canConfigureService,
            }

            if (section !== 'service-catalogue' && capabilities.canConfigureService) {
              configureWorkspaceProps.onSave = (input) => configureService.mutate(input)
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
          services={workspace?.services ?? []}
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

      {section === 'service-catalogue' && capabilities.canCreateInitialServiceSetup ? (
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
