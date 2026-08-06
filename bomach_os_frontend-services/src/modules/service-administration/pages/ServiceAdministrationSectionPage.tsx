import { IconPlus, IconRefresh } from '@tabler/icons-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import {
  CalculatorEditor,
  RequestFormEditor,
  WorkflowEditor,
} from '../editors/ServiceAdministrationEditors'

import { presentError } from '@/shared/errors'
import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'

import { serviceAdministrationApi } from '../api/service-administration.api'
import { serviceAdministrationKeys } from '../api/service-administration.keys'
import { serviceAdministrationQueries } from '../api/service-administration.queries'
import {
  BranchMatrix,
  CompactPageToolbar,
  NewServiceDialog,
  PrototypeButton,
  SectionCard,
  ServiceDetailPanel,
} from '../components/ServiceAdministrationUi'
import { serviceAdministrationIcons } from '../components/service-administration.icons'
import {
  ExactCalculatorLibrary,
  ExactRequestFormBuilder,
  ExactServiceCatalogue,
  ExactWorkflowDesigner,
} from '../prototype/PrototypeExactScreens'
import type {
  BranchActivation,
  CreateServiceInput,
  PricingCalculator,
  ServiceCatalogueItem,
  ServiceRequestForm,
  ServiceWorkflow,
  SaveCalculatorInput,
  SaveRequestFormInput,
  SaveWorkflowInput,
  UpdateBranchActivationInput,
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
  const [selectedService, setSelectedService] = useState<ServiceCatalogueItem | null>(null)
  const [newServiceOpen, setNewServiceOpen] = useState(false)
  const [calculatorEditor, setCalculatorEditor] = useState<PricingCalculator | null | 'new'>(null)
  const [formEditor, setFormEditor] = useState<ServiceRequestForm | null | 'new'>(null)
  const [workflowEditor, setWorkflowEditor] = useState<ServiceWorkflow | null | 'new'>(null)

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

  const duplicateService = useMutation({
    mutationFn: (input: { id: string }) => serviceAdministrationApi.duplicateService(input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: serviceAdministrationKeys.all })
      toast.success('Service duplicated as draft')
    },
  })

  const saveCalculator = useMutation({
    mutationFn: (input: SaveCalculatorInput) => serviceAdministrationApi.saveCalculator(input),
    onSuccess: (workspace) => {
      queryClient.setQueryData(serviceAdministrationKeys.workspace(), workspace)
      setCalculatorEditor(null)
      toast.success('Calculator saved')
    },
  })

  const saveRequestForm = useMutation({
    mutationFn: (input: SaveRequestFormInput) => serviceAdministrationApi.saveRequestForm(input),
    onSuccess: (workspace) => {
      queryClient.setQueryData(serviceAdministrationKeys.workspace(), workspace)
      setFormEditor(null)
      toast.success('Request form saved')
    },
  })

  const saveWorkflow = useMutation({
    mutationFn: (input: SaveWorkflowInput) => serviceAdministrationApi.saveWorkflow(input),
    onSuccess: (workspace) => {
      queryClient.setQueryData(serviceAdministrationKeys.workspace(), workspace)
      setWorkflowEditor(null)
      toast.success('Workflow saved')
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

  const toolbarPrimary =
    section === 'service-catalogue' ? (
      <PrototypeButton tone="primary" onClick={() => setNewServiceOpen(true)}>
        <IconPlus size={14} />
        Create Service
      </PrototypeButton>
    ) : (
      <PrototypeButton
        tone="primary"
        onClick={() => {
          if (section === 'calculator-library') setCalculatorEditor('new')
          if (section === 'request-form-builder') setFormEditor('new')
          if (section === 'workflow-designer') setWorkflowEditor('new')
        }}
      >
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

      {section === 'service-catalogue' ? (
        <ExactServiceCatalogue
          services={workspace.services}
          onConfigure={setSelectedService}
          onDuplicate={(service) => duplicateService.mutate({ id: service.id })}
        />
      ) : null}

      {section === 'calculator-library' ? (
        <ExactCalculatorLibrary
          calculators={workspace.calculators}
          onCreate={() => setCalculatorEditor('new')}
        />
      ) : null}

      {section === 'request-form-builder' ? (
        <ExactRequestFormBuilder
          forms={workspace.requestForms}
          onCreate={() => setFormEditor('new')}
        />
      ) : null}

      {section === 'workflow-designer' ? (
        <ExactWorkflowDesigner
          workflows={workspace.workflows}
          onCreate={() => setWorkflowEditor('new')}
        />
      ) : null}

      {section === 'branch-activation' ? (
        <main className="prototype-page prototype-content">
          <SectionCard
            title="Branch Activation"
            description="Service availability and branch capacity"
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
        </main>
      ) : null}

      {selectedService ? (
        <ServiceDetailPanel service={selectedService} onClose={() => setSelectedService(null)} />
      ) : null}

      {calculatorEditor ? (
        <CalculatorEditor
          {...(calculatorEditor === 'new' ? {} : { calculator: calculatorEditor })}
          services={workspace.services}
          onClose={() => setCalculatorEditor(null)}
          onSave={(input) => saveCalculator.mutate(input)}
          saving={saveCalculator.isPending}
        />
      ) : null}

      {formEditor ? (
        <RequestFormEditor
          {...(formEditor === 'new' ? {} : { form: formEditor })}
          services={workspace.services}
          onClose={() => setFormEditor(null)}
          onSave={(input) => saveRequestForm.mutate(input)}
          saving={saveRequestForm.isPending}
        />
      ) : null}

      {workflowEditor ? (
        <WorkflowEditor
          {...(workflowEditor === 'new' ? {} : { workflow: workflowEditor })}
          services={workspace.services}
          onClose={() => setWorkflowEditor(null)}
          onSave={(input) => saveWorkflow.mutate(input)}
          saving={saveWorkflow.isPending}
        />
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
