import { IconFilePlus, IconPlus } from '@tabler/icons-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useState } from 'react'

import { useAuth } from '@/app/auth'
import { SectionLoadingState } from '@/app/loading/SectionLoadingState'

import { CalculatorEditor, RequestFormEditor } from '../editors/ServiceAdministrationEditors'
import {
  ConfigureServiceWorkspace,
  CreateServiceWizard,
} from '../workspaces/ServiceCatalogueWorkspaces'

import { presentError } from '@/shared/errors'
import { ApiError } from '@/shared/api/api-error'
import { ErrorState, useToast } from '@/shared/ui'
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
  saveLivePricingConfig,
  saveLiveRequestForm,
  saveLiveWorkflow,
  publishLiveService,
} from '../api/service-administration.live-mutations'
import { serviceAdministrationQueries } from '../api/service-administration.queries'
import { runLiveServiceSetup } from '../api/service-setup.orchestrator'
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
  ServiceSetupStageProgress,
  ServiceSetupStageId,
  CreateServiceStageAccess,
  PricingCalculator,
  ServiceCatalogueItem,
  ServiceRequestForm,
  ServiceWorkflow,
  WorkflowOwnerRoleOption,
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
  const createStageAccess: CreateServiceStageAccess = {
    subservices: capabilities.canUpdateSubservices,
    pricing: capabilities.canCreatePricingConfig,
    requestForm: capabilities.canCreateRequestForm,
    workflow: capabilities.canCreateWorkflow,
    branches: capabilities.canListBranches && capabilities.canUpdateBranchActivations,
    publish: capabilities.canPublishService,
    ownerRoles: capabilities.canListRoles,
  }
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
    enabled: true,
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
    enabled:
      capabilities.canListRoles &&
      (section === 'workflow-designer' || capabilities.canCreateInitialServiceSetup),
  })
  const createWizardBranchesQuery = useQuery({
    ...serviceAdministrationQueries.branches(),
    enabled: capabilities.canCreateInitialServiceSetup && capabilities.canListBranches,
  })
  const branchMatrixQuery = useQuery({
    ...serviceAdministrationQueries.branchActivationMatrix(),
    enabled: section === 'branch-activation' && capabilities.canListBranchActivations,
  })
  const [selectedService, setSelectedService] = useState<ServiceCatalogueItem | null>(null)
  const [newServiceOpen, setNewServiceOpen] = useState(false)
  const [serviceSetupProgress, setServiceSetupProgress] = useState<ServiceSetupStageProgress[]>([])
  const [serviceSetupId, setServiceSetupId] = useState<number | null>(null)
  const [lastServiceSetupInput, setLastServiceSetupInput] =
    useState<CreateServiceWizardInput | null>(null)
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

  const mergeSetupProgress = (stage: ServiceSetupStageProgress) => {
    setServiceSetupProgress((current) => {
      const found = current.some((item) => item.id === stage.id)
      return found
        ? current.map((item) => (item.id === stage.id ? stage : item))
        : [...current, stage]
    })
  }

  const createService = useMutation({
    mutationFn: async (input: CreateServiceWizardInput) => {
      setLastServiceSetupInput(input)
      setServiceSetupId(null)
      setServiceSetupProgress([])
      return runLiveServiceSetup(input, createStageAccess, { onProgress: mergeSetupProgress })
    },
    onSuccess: async (result) => {
      setServiceSetupId(result.serviceId)
      await queryClient.invalidateQueries({ queryKey: serviceAdministrationKeys.catalogue() })
      const needsAttention = result.stages.some(
        (stage) => stage.state === 'failed' || stage.state === 'skipped',
      )
      if (!needsAttention) {
        setNewServiceOpen(false)
        setServiceSetupProgress([])
        setServiceSetupId(null)
        setLastServiceSetupInput(null)
        toast.success('Service setup completed')
        return
      }
      toast.error('Service created with setup items requiring attention', {
        description: result.stages
          .filter((stage) => stage.state === 'failed' || stage.state === 'skipped')
          .map((stage) => stage.label)
          .join(', '),
      })
    },
    onError: async (error) => {
      await queryClient.invalidateQueries({ queryKey: serviceAdministrationKeys.catalogue() })
      const presented = presentError(error, 'background-action')
      toast.error('Service could not be created', { description: presented.message })
    },
  })

  const retryServiceSetup = useMutation({
    mutationFn: async () => {
      if (!lastServiceSetupInput || !serviceSetupId) {
        throw new Error('There is no partial Service setup to retry.')
      }
      const retryStages = serviceSetupProgress
        .filter((stage) => stage.state === 'failed' || stage.state === 'skipped')
        .map((stage) => stage.id)
        .filter((stage): stage is ServiceSetupStageId => stage !== 'service-core')
      return runLiveServiceSetup(lastServiceSetupInput, createStageAccess, {
        existingServiceId: serviceSetupId,
        onlyStages: retryStages,
        onProgress: mergeSetupProgress,
      })
    },
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: serviceAdministrationKeys.catalogue() })
      const merged = new Map(serviceSetupProgress.map((stage) => [stage.id, stage]))
      result.stages.forEach((stage) => merged.set(stage.id, stage))
      const remaining = [...merged.values()].filter(
        (stage) => stage.state === 'failed' || stage.state === 'skipped',
      )
      if (remaining.length === 0) {
        setNewServiceOpen(false)
        setServiceSetupProgress([])
        setServiceSetupId(null)
        setLastServiceSetupInput(null)
        toast.success('Service setup completed')
      } else {
        toast.error('Some setup items still need attention', {
          description: remaining.map((stage) => stage.label).join(', '),
        })
      }
    },
    onError: (error) => {
      const presented = presentError(error, 'background-action')
      toast.error('Setup retry failed', { description: presented.message })
    },
  })

  const saveCalculator = useMutation({
    mutationFn: (input: SaveCalculatorInput) => {
      const existingCalculator = input.id
        ? null
        : (pricingQuery.data?.find((calculator) => calculator.serviceId === input.serviceId) ??
          null)

      return saveLivePricingConfig(
        existingCalculator ? { ...input, id: existingCalculator.id } : input,
      )
    },
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

  const saveConfiguredService = useMutation({
    mutationFn: async (input: ConfigureServiceInput) => {
      const serviceId = Number(input.id)
      if (!Number.isFinite(serviceId) || serviceId <= 0) {
        throw new Error('The selected service has an invalid backend identifier.')
      }

      const ownerRole =
        rolesQuery.data?.find((role) => role.id === input.ownerRoleId) ??
        rolesQuery.data?.find((role) => role.name === input.owner) ??
        null
      const branchOptions = createWizardBranchesQuery.data ?? []
      const selectedBranchNames = new Set(input.branchNames)

      const fulfillmentModeMap: Record<string, string> = {
        'quick service order': 'quick_order',
        'managed service case': 'managed_case',
        'project & worksite': 'project_worksite',
        'transaction & allocation': 'transaction_allocation',
        'supply order': 'supply_order',
      }

      const pricingTypeMap: Record<
        string,
        'fixed' | 'unit_rate' | 'area_rate' | 'percentage' | 'formula'
      > = {
        fixed: 'fixed',
        'unit rate': 'unit_rate',
        'area rate': 'area_rate',
        percentage: 'percentage',
        'custom formula': 'formula',
      }

      const requestFieldType = (label: string) => {
        const normalized = label.toLowerCase()
        if (normalized.includes('budget')) return 'money' as const
        if (normalized.includes('date')) return 'date' as const
        if (normalized.includes('scope') || normalized.includes('message'))
          return 'textarea' as const
        if (
          normalized.includes('upload') ||
          normalized.includes('document') ||
          normalized.includes('image')
        ) {
          return 'file' as const
        }
        if (normalized.includes('location') || normalized.includes('site'))
          return 'location' as const
        if (normalized.includes('consent')) return 'checkbox' as const
        if (normalized.includes('phone')) return 'phone' as const
        if (normalized.includes('email')) return 'email' as const
        return 'text' as const
      }

      await serviceAdministrationBackendApi.updateService(serviceId, {
        name: input.name,
        code: input.code || null,
        division: input.division,
        description: input.description,
        status: input.status,
        ...(ownerRole ? { owner_role_id: ownerRole.id } : {}),
        default_sla_days: input.slaDays,
        fulfillment_mode:
          fulfillmentModeMap[input.fulfilmentMode.trim().toLowerCase()] ?? input.fulfilmentMode,
        client_visibility: 'visible',
      })

      await serviceAdministrationBackendApi.replaceSubservices(
        serviceId,
        input.subservices.map((name, index) => ({
          name,
          status: input.status === 'inactive' ? 'archived' : 'draft',
          default_sla_days: input.slaDays,
          sort_order: index,
        })),
      )

      await saveLivePricingConfig({
        ...(selectedCalculator ? { id: selectedCalculator.id } : {}),
        name: selectedCalculator?.name ?? `${input.name} Pricing`,
        code: selectedCalculator?.code ?? `${input.code || input.name}-pricing`,
        serviceId: input.id,
        description: selectedCalculator?.description ?? `Pricing for ${input.name}`,
        pricingType: pricingTypeMap[input.pricing.method.trim().toLowerCase()] ?? 'fixed',
        status: input.status === 'inactive' ? 'inactive' : 'draft',
        variables: selectedCalculator?.variables ?? [],
        charges: [
          {
            id:
              selectedCalculator?.charges.find((charge) => charge.label === 'Formula')?.id ??
              'formula',
            label: 'Formula',
            kind:
              (pricingTypeMap[input.pricing.method.trim().toLowerCase()] ?? 'fixed') === 'formula'
                ? 'formula'
                : 'fixed',
            value:
              (pricingTypeMap[input.pricing.method.trim().toLowerCase()] ?? 'fixed') === 'formula'
                ? 'quantity * unit_rate + logistics'
                : input.pricing.rate,
          },
          {
            id:
              selectedCalculator?.charges.find((charge) =>
                charge.label.toLowerCase().includes('deposit'),
              )?.id ?? 'deposit',
            label: 'Deposit',
            kind: 'percentage',
            value: input.pricing.depositPercent,
          },
          {
            id:
              selectedCalculator?.charges.find((charge) =>
                charge.label.toLowerCase().includes('tax'),
              )?.id ?? 'tax',
            label: 'Tax',
            kind: 'percentage',
            value: input.pricing.taxPercent,
          },
          {
            id:
              selectedCalculator?.charges.find((charge) =>
                charge.label.toLowerCase().includes('approval'),
              )?.id ?? 'approval',
            label: 'Discount approval',
            kind: 'percentage',
            value: input.pricing.discountApprovalPercent,
          },
        ],
        sampleTotal: input.pricing.rate,
      })

      await saveLiveRequestForm(
        {
          ...(selectedRequestForm ? { id: selectedRequestForm.id } : {}),
          name: selectedRequestForm?.name ?? `${input.name} Request Form`,
          serviceId: input.id,
          status: input.status === 'inactive' ? 'inactive' : 'draft',
          fields: input.requestFields.map((label, index) => ({
            id: selectedRequestForm?.fields[index]?.id ?? `field-${index + 1}`,
            label,
            key: label
              .toLowerCase()
              .replace(/[^a-z0-9]+/g, '_')
              .replace(/^_|_$/g, ''),
            type: selectedRequestForm?.fields[index]?.type ?? requestFieldType(label),
            required: selectedRequestForm?.fields[index]?.required ?? true,
          })),
        },
        input.name,
      )

      await saveLiveWorkflow(
        {
          ...(selectedWorkflow ? { id: selectedWorkflow.id } : {}),
          name: selectedWorkflow?.name ?? `${input.name} Workflow`,
          serviceId: input.id,
          status: input.status === 'inactive' ? 'inactive' : 'draft',
          stages: input.workflowStages.map((name, index) => ({
            id: selectedWorkflow?.stages[index]?.id ?? `stage-${index + 1}`,
            name,
            order: index + 1,
            ownerRole: selectedWorkflow?.stages[index]?.ownerRole ?? input.owner,
            ownerRoleId: selectedWorkflow?.stages[index]?.ownerRoleId ?? ownerRole?.id ?? null,
            slaHours: selectedWorkflow?.stages[index]?.slaHours ?? 24,
            requiresEvidence: selectedWorkflow?.stages[index]?.requiresEvidence ?? index > 0,
            requiresApproval: selectedWorkflow?.stages[index]?.requiresApproval ?? false,
            clientVisible: selectedWorkflow?.stages[index]?.clientVisible ?? true,
          })),
        },
        input.name,
      )

      await serviceAdministrationBackendApi.upsertBranchActivations(
        serviceId,
        branchOptions.map((branch) => ({
          branch_id: branch.id,
          status: selectedBranchNames.has(branch.name) ? 'active' : 'inactive',
          client_visible: true,
          capacity: 80,
          activated_at: selectedBranchNames.has(branch.name) ? new Date().toISOString() : null,
        })),
      )

      return queryClient.fetchQuery(serviceAdministrationQueries.catalogueDetail(serviceId))
    },
    onSuccess: async (service) => {
      await queryClient.invalidateQueries({ queryKey: serviceAdministrationKeys.catalogue() })
      setSelectedService(service)
      toast.success('Service configuration saved')
    },
    onError: (error) => {
      const presented = presentError(error, 'background-action')
      toast.error('Service configuration could not be saved', {
        description: presented.message,
      })
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
    section === 'calculator-library'
      ? pricingQuery
      : section === 'branch-activation'
        ? branchMatrixQuery
        : catalogueQuery

  if (activeQuery.isLoading) return <SectionLoadingState section={section} />
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
    return <SectionLoadingState section={section} />
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

  const catalogue = catalogueQuery.data
  const page = metadata[section]
  const selectedCalculator = selectedService?.activeCalculator
  const selectedRequestForm = selectedService?.activeRequestForm
  const selectedWorkflow = selectedService?.activeWorkflow

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
            configureLabel={capabilities.canUpdateService ? 'Configure' : 'View'}
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
              branches?: Array<{ id: number; name: string; code: string }>
              ownerRoles?: WorkflowOwnerRoleOption[]
              calculator?: PricingCalculator
              requestForm?: ServiceRequestForm
              workflow?: ServiceWorkflow
            } = {
              service: selectedService,
              pending: saveConfiguredService.isPending,
              onClose: () => setSelectedService(null),
              readOnly: !capabilities.canUpdateService,
            }

            if (capabilities.canUpdateService) {
              configureWorkspaceProps.onSave = (input: ConfigureServiceInput) =>
                saveConfiguredService.mutate(input)
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

            configureWorkspaceProps.branches = createWizardBranchesQuery.data ?? []
            configureWorkspaceProps.ownerRoles = rolesQuery.data ?? []

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

      {capabilities.canCreateInitialServiceSetup && newServiceOpen ? (
        <CreateServiceWizard
          open
          categories={categoryQuery.data ?? []}
          branches={createWizardBranchesQuery.data ?? []}
          ownerRoles={rolesQuery.data ?? []}
          stageAccess={createStageAccess}
          progress={serviceSetupProgress}
          setupServiceId={serviceSetupId}
          onClose={() => {
            setNewServiceOpen(false)
            setServiceSetupProgress([])
            setServiceSetupId(null)
            setLastServiceSetupInput(null)
          }}
          pending={createService.isPending || retryServiceSetup.isPending}
          onSubmit={(value) => createService.mutate(value)}
          onRetryFailed={() => retryServiceSetup.mutate()}
        />
      ) : null}
    </>
  )
}
