import { IconPlus, IconRefresh } from '@tabler/icons-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { presentError } from '@/shared/errors'
import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'

import { serviceAdministrationApi } from '../api/service-administration.api'
import { serviceAdministrationKeys } from '../api/service-administration.keys'
import { serviceAdministrationQueries } from '../api/service-administration.queries'
import {
  BranchMatrix,
  CalculatorList,
  CompactPageToolbar,
  NewServiceDialog,
  PrototypeButton,
  PrototypeFilterBar,
  PrototypeSelect,
  RequestFormCards,
  SectionCard,
  ServiceCatalogueGrid,
  ServiceDetailPanel,
  SummaryStrip,
  WorkflowCards,
} from '../components/ServiceAdministrationUi'
import { serviceAdministrationIcons } from '../components/service-administration.icons'
import type {
  BranchActivation,
  CreateServiceInput,
  PricingCalculator,
  ServiceCatalogueItem,
  ServiceRequestForm,
  ServiceWorkflow,
  UpdateBranchActivationInput,
  UpdateConfigurationStatusInput,
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
    breadcrumb: 'Services / Service Administration / Catalogue',
    description: 'Configure the services Bomach can sell and fulfil.',
  },
  'calculator-library': {
    title: 'Calculator Library',
    breadcrumb: 'Services / Service Administration / Calculators',
    description: 'Create and manage reusable service pricing calculators.',
  },
  'request-form-builder': {
    title: 'Request Form Builder',
    breadcrumb: 'Services / Service Administration / Request Forms',
    description: 'Design the intake fields used for each service request.',
  },
  'workflow-designer': {
    title: 'Workflow Designer',
    breadcrumb: 'Services / Service Administration / Workflows',
    description: 'Define fulfilment stages, ownership, SLA and controls.',
  },
  'branch-activation': {
    title: 'Branch Activation',
    breadcrumb: 'Services / Service Administration / Branches',
    description: 'Control where each service can be offered and delivered.',
  },
}

export function ServiceAdministrationSectionPage({
  section,
}: {
  section: ServiceAdministrationSection
}) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const query = useQuery(serviceAdministrationQueries.workspace())
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [division, setDivision] = useState('')
  const [selectedService, setSelectedService] = useState<ServiceCatalogueItem | null>(null)
  const [newServiceOpen, setNewServiceOpen] = useState(false)

  const createService = useMutation<
    Awaited<ReturnType<typeof serviceAdministrationApi.createService>>,
    Error,
    CreateServiceInput
  >({
    mutationFn: (input) => serviceAdministrationApi.createService(input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: serviceAdministrationKeys.all })
      setNewServiceOpen(false)
      toast.success('Draft service created', {
        description: 'Continue with pricing, request form, workflow and branch activation.',
      })
    },
  })

  const updateStatus = useMutation<
    Awaited<ReturnType<typeof serviceAdministrationApi.updateStatus>>,
    Error,
    UpdateConfigurationStatusInput
  >({
    mutationFn: (input) => serviceAdministrationApi.updateStatus(input),
    onSuccess: (workspace) => {
      queryClient.setQueryData(serviceAdministrationKeys.workspace(), workspace)
      toast.success('Configuration updated')
    },
  })

  const updateBranch = useMutation<
    Awaited<ReturnType<typeof serviceAdministrationApi.updateBranchActivation>>,
    Error,
    UpdateBranchActivationInput
  >({
    mutationFn: (input) => serviceAdministrationApi.updateBranchActivation(input),
    onSuccess: (workspace) => {
      queryClient.setQueryData(serviceAdministrationKeys.workspace(), workspace)
      toast.success('Branch activation updated')
    },
  })

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

  const workspace = query.data
  const page = metadata[section]

  const filteredServices = workspace.services.filter((item) => {
    const matchesSearch = [item.name, item.code, item.division, item.owner]
      .join(' ')
      .toLowerCase()
      .includes(search.toLowerCase())
    return (
      matchesSearch &&
      (!status || item.status === status) &&
      (!division || item.division === division)
    )
  })

  const divisions = Array.from(new Set(workspace.services.map((item) => item.division)))

  const filteredCalculators = workspace.calculators.filter((item) =>
    [item.name, item.code, item.serviceName].join(' ').toLowerCase().includes(search.toLowerCase()),
  )
  const filteredForms = workspace.requestForms.filter((item) =>
    [item.name, item.serviceName].join(' ').toLowerCase().includes(search.toLowerCase()),
  )
  const filteredWorkflows = workspace.workflows.filter((item) =>
    [item.name, item.serviceName].join(' ').toLowerCase().includes(search.toLowerCase()),
  )

  const toolbarPrimary =
    section === 'service-catalogue' ? (
      <PrototypeButton tone="primary" onClick={() => setNewServiceOpen(true)}>
        <IconPlus size={14} />
        Create Service
      </PrototypeButton>
    ) : (
      <PrototypeButton tone="primary">
        <IconPlus size={14} />
        {section === 'calculator-library'
          ? 'New Calculator'
          : section === 'request-form-builder'
            ? 'New Request Form'
            : section === 'workflow-designer'
              ? 'New Workflow'
              : 'Update Activations'}
      </PrototypeButton>
    )

  return (
    <>
      <CompactPageToolbar
        title={page.title}
        breadcrumb={page.breadcrumb}
        primaryAction={toolbarPrimary}
        secondaryAction={
          <PrototypeButton onClick={() => void query.refetch()}>
            <IconRefresh size={14} />
            Refresh
          </PrototypeButton>
        }
      />

      <main className="space-y-3 p-3 sm:p-4 lg:p-5">
        <SummaryStrip
          items={[
            { label: 'Services', value: workspace.summary.totalServices },
            { label: 'Active', value: workspace.summary.activeServices },
            { label: 'Draft', value: workspace.summary.draftServices },
            { label: 'Branches covered', value: workspace.summary.branchesCovered },
            {
              label: 'Configuration issues',
              value: workspace.summary.configurationIssues,
              note: 'Needs attention',
            },
          ]}
        />

        <PrototypeFilterBar search={search} onSearch={setSearch}>
          {section === 'service-catalogue' ? (
            <>
              <PrototypeSelect label="Status" value={status} onChange={setStatus}>
                <option value="">All</option>
                <option value="active">Active</option>
                <option value="draft">Draft</option>
                <option value="inactive">Inactive</option>
              </PrototypeSelect>
              <PrototypeSelect label="Division" value={division} onChange={setDivision}>
                <option value="">All</option>
                {divisions.map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </PrototypeSelect>
            </>
          ) : null}
        </PrototypeFilterBar>

        {section === 'service-catalogue' ? (
          <SectionCard
            title="Configured Services"
            description={page.description}
            icon={serviceAdministrationIcons.catalogue}
          >
            <div className="p-3">
              <ServiceCatalogueGrid services={filteredServices} onSelect={setSelectedService} />
            </div>
          </SectionCard>
        ) : null}

        {section === 'calculator-library' ? (
          <SectionCard
            title="Pricing Calculators"
            description={page.description}
            icon={serviceAdministrationIcons.calculators}
          >
            <div className="p-3">
              <CalculatorList
                calculators={filteredCalculators}
                onToggle={(item: PricingCalculator) =>
                  updateStatus.mutate({
                    entity: 'calculator',
                    id: item.id,
                    status: item.status === 'active' ? 'inactive' : 'active',
                  })
                }
              />
            </div>
          </SectionCard>
        ) : null}

        {section === 'request-form-builder' ? (
          <SectionCard
            title="Service Request Forms"
            description={page.description}
            icon={serviceAdministrationIcons.forms}
          >
            <div className="p-3">
              <RequestFormCards
                forms={filteredForms}
                onToggle={(item: ServiceRequestForm) =>
                  updateStatus.mutate({
                    entity: 'request-form',
                    id: item.id,
                    status: item.status === 'active' ? 'draft' : 'active',
                  })
                }
              />
            </div>
          </SectionCard>
        ) : null}

        {section === 'workflow-designer' ? (
          <SectionCard
            title="Service Workflows"
            description={page.description}
            icon={serviceAdministrationIcons.workflows}
          >
            <div className="p-3">
              <WorkflowCards
                workflows={filteredWorkflows}
                onToggle={(item: ServiceWorkflow) =>
                  updateStatus.mutate({
                    entity: 'workflow',
                    id: item.id,
                    status: item.status === 'active' ? 'draft' : 'active',
                  })
                }
              />
            </div>
          </SectionCard>
        ) : null}

        {section === 'branch-activation' ? (
          <SectionCard
            title="Service × Branch Activation Matrix"
            description={page.description}
            icon={serviceAdministrationIcons.branches}
          >
            <div className="p-3">
              <BranchMatrix
                activations={workspace.branchActivations}
                onToggle={(item: BranchActivation) =>
                  updateBranch.mutate({
                    id: item.id,
                    state:
                      item.state === 'active'
                        ? 'inactive'
                        : item.state === 'inactive'
                          ? 'setup-required'
                          : 'active',
                  })
                }
              />
            </div>
          </SectionCard>
        ) : null}
      </main>

      {selectedService ? (
        <ServiceDetailPanel service={selectedService} onClose={() => setSelectedService(null)} />
      ) : null}

      <NewServiceDialog
        open={newServiceOpen}
        onClose={() => setNewServiceOpen(false)}
        pending={createService.isPending}
        onSubmit={(value) => createService.mutate(value)}
      />
    </>
  )
}
