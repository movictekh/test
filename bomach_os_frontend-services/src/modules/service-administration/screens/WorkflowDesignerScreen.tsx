import { IconSubtask } from '@tabler/icons-react'
import { useMemo, useState } from 'react'

import { AccessLockIcon } from '@/shared/ui/module-controls'
import { useToast } from '@/shared/ui'
import { formatNumberFieldValue, parseNumberFieldValue } from '@/shared/lib/number-input'

import { AutomationRulesPanel } from '../components/AutomationRulesPanel'

import type {
  SaveWorkflowInput,
  ServiceCatalogueItem,
  ServiceWorkflow,
  WorkflowOwnerRoleOption,
  WorkflowStage,
} from '../types/service-administration.types'

const fulfillmentModes = [
  ['Quick Service Order', 'Short work without a full project'],
  ['Managed Service Case', 'Recurring or retained service'],
  ['Project & Worksite', 'Engineering and multi-milestone work'],
] as const

function hoursToDays(hours: number) {
  return Math.max(1, Math.round(hours / 24) || 1)
}

function daysToHours(days: number) {
  return Math.max(1, days) * 24
}

function cloneStages(stages: WorkflowStage[]) {
  return stages
    .slice()
    .sort((a, b) => a.order - b.order)
    .map((stage) => ({ ...stage }))
}

function stagesFromNames(names: string[], ownerRoles: WorkflowOwnerRoleOption[]): WorkflowStage[] {
  return names.map((name, index) => {
    const role = ownerRoles[Math.min(index, Math.max(0, ownerRoles.length - 1))]
    return {
      id: `stage-seed-${index}-${name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
      name,
      order: index + 1,
      ownerRole: role?.name ?? 'Unassigned',
      ownerRoleId: role?.id ?? null,
      slaHours: daysToHours(index === 0 ? 1 : 2),
      requiresApproval: /Approval|Review|Payment|Inspection/i.test(name),
      requiresEvidence: index > 1,
      clientVisible: true,
    }
  })
}

function buildStagesForService(
  service: ServiceCatalogueItem,
  workflow: ServiceWorkflow | undefined,
  ownerRoles: WorkflowOwnerRoleOption[],
): WorkflowStage[] {
  if (workflow?.stages.length) return cloneStages(workflow.stages)
  if (service.workflowStages?.length) return stagesFromNames(service.workflowStages, ownerRoles)
  return stagesFromNames(
    ['Request Review', 'Execution', 'Quality Review', 'Client Acceptance'],
    ownerRoles,
  )
}

type StageDraft = {
  name: string
  ownerRole: string
  ownerRoleId: number | null
  slaDays: number
  requiresApproval: boolean
  requiresEvidence: boolean
}

function stageToDraft(stage: WorkflowStage): StageDraft {
  return {
    name: stage.name,
    ownerRole: stage.ownerRole,
    ownerRoleId: stage.ownerRoleId ?? null,
    slaDays: hoursToDays(stage.slaHours),
    requiresApproval: stage.requiresApproval,
    requiresEvidence: stage.requiresEvidence,
  }
}

export function WorkflowDesignerScreen({
  services,
  workflows,
  selectedServiceId,
  onSelectedServiceChange,
  ownerRoles,
  saving,
  onSave,
}: {
  services: ServiceCatalogueItem[]
  workflows: ServiceWorkflow[]
  selectedServiceId: string
  onSelectedServiceChange: (serviceId: string) => void
  ownerRoles: WorkflowOwnerRoleOption[]
  saving: boolean
  onSave?: (input: SaveWorkflowInput) => void
}) {
  const canEdit = Boolean(onSave)
  const toast = useToast()

  const selectedService =
    services.find((service) => service.id === selectedServiceId) ?? services[0]

  const linkedWorkflow = useMemo(() => {
    if (!selectedService) return undefined
    return (
      workflows.find((workflow) => workflow.serviceId === selectedService.id) ??
      workflows.find((workflow) => workflow.serviceName === selectedService.name)
    )
  }, [selectedService, workflows])

  const sourceKey = `${selectedService?.id ?? ''}:${linkedWorkflow?.id ?? ''}:${linkedWorkflow?.updatedAt ?? ''}`

  const [draftKey, setDraftKey] = useState(sourceKey)
  const [stages, setStages] = useState<WorkflowStage[]>(() =>
    selectedService ? buildStagesForService(selectedService, linkedWorkflow, ownerRoles) : [],
  )
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [stageDraft, setStageDraft] = useState<StageDraft | null>(null)

  if (sourceKey !== draftKey && selectedService) {
    setDraftKey(sourceKey)
    setStages(buildStagesForService(selectedService, linkedWorkflow, ownerRoles))
    setEditingIndex(null)
    setStageDraft(null)
  }

  const openEdit = (index: number) => {
    const stage = stages[index]
    if (!stage) return
    setEditingIndex(index)
    setStageDraft(stageToDraft(stage))
  }

  const addStage = () => {
    setStages((current) => [
      ...current,
      {
        id: `stage-new-${Date.now()}`,
        name: 'New Stage',
        order: current.length + 1,
        ownerRole: ownerRoles[0]?.name ?? 'Unassigned',
        ownerRoleId: ownerRoles[0]?.id ?? null,
        slaHours: 24,
        requiresApproval: false,
        requiresEvidence: true,
        clientVisible: true,
      },
    ])
  }

  const deleteStage = (index: number) => {
    setStages((current) =>
      current
        .filter((_, itemIndex) => itemIndex !== index)
        .map((stage, orderIndex) => ({ ...stage, order: orderIndex + 1 })),
    )
  }

  const applyStageEdit = () => {
    if (editingIndex === null || !stageDraft) return
    const name = stageDraft.name.trim()
    if (!name) {
      toast.error('Stage name is required')
      return
    }

    setStages((current) =>
      current.map((stage, index) =>
        index === editingIndex
          ? {
              ...stage,
              name,
              ownerRole: stageDraft.ownerRole,
              ownerRoleId: stageDraft.ownerRoleId,
              slaHours: daysToHours(stageDraft.slaDays),
              requiresApproval: stageDraft.requiresApproval,
              requiresEvidence: stageDraft.requiresEvidence,
            }
          : stage,
      ),
    )
    setEditingIndex(null)
    setStageDraft(null)
  }

  const saveWorkflow = () => {
    if (!selectedService) return
    if (stages.length === 0) {
      toast.error('Add at least one workflow stage')
      return
    }

    if (!onSave) return

    onSave({
      ...(linkedWorkflow?.id ? { id: linkedWorkflow.id } : {}),
      name: linkedWorkflow?.name ?? `${selectedService.name} Workflow`,
      serviceId: selectedService.id,
      status: linkedWorkflow?.status ?? 'active',
      stages: stages.map((stage, index) => ({ ...stage, order: index + 1 })),
    })
  }

  if (!selectedService) {
    return (
      <div className="service-admin-page service-admin-content">
        <div className="service-admin-card">
          <div className="service-admin-card-header">
            <div>
              <div className="service-admin-card-title">Workflow & Fulfillment Designer</div>
              <div className="service-admin-card-subtitle">
                Stages, owners, SLAs, approvals, evidence and client checkpoints
              </div>
            </div>
            <div className="service-admin-acts">
              <select aria-label="Select service" disabled value="">
                <option value="">No services available</option>
              </select>
              <button type="button" className="service-admin-button" disabled>
                Add Stage
              </button>
              <button
                type="button"
                className="service-admin-button service-admin-button-primary"
                disabled
              >
                Save Workflow
              </button>
            </div>
          </div>

          <div className="service-admin-table-wrap" style={{ marginTop: 12 }}>
            <table className="service-admin-table service-admin-workflow-table">
              <thead>
                <tr>
                  <th>Stage</th>
                  <th>Owner</th>
                  <th>SLA</th>
                  <th>Approval</th>
                  <th>Evidence</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td colSpan={6}>
                    <div className="py-8 text-center" role="status">
                      <div className="service-admin-card-title">No workflow to configure yet</div>
                      <div className="service-admin-card-subtitle mt-1">
                        Create a service first. Its workflow stages will then be configured here in
                        the same layout.
                      </div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div className="service-admin-g2">
          <div className="service-admin-card">
            <div className="service-admin-card-header">
              <div className="service-admin-card-title">Automation Rules</div>
              <button
                type="button"
                className="service-admin-button service-admin-button-small"
                disabled
              >
                Add Rule
              </button>
            </div>
            <div className="service-admin-card-subtitle py-5">
              Automation rules will appear here after a workflow exists.
            </div>
          </div>

          <div className="service-admin-card">
            <div className="service-admin-card-header">
              <div className="service-admin-card-title">Fulfillment Modes</div>
            </div>
            {fulfillmentModes.map(([title, description]) => (
              <div key={title} className="service-admin-list-row opacity-60">
                <div className="service-admin-list-ico service-admin-list-ico--mode">
                  <IconSubtask size={16} aria-hidden="true" />
                </div>
                <div className="service-admin-list-meta">
                  <div className="service-admin-list-name">{title}</div>
                  <div className="service-admin-list-sub">{description}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="service-admin-page service-admin-content">
      <div className="service-admin-card">
        <div className="service-admin-card-header">
          <div>
            <div className="service-admin-card-title">Workflow & Fulfillment Designer</div>
            <div className="service-admin-card-subtitle">
              Stages, owners, SLAs, approvals, evidence and client checkpoints
            </div>
          </div>
          <div className="service-admin-acts">
            <select
              aria-label="Select service"
              value={selectedService.id}
              onChange={(event) => onSelectedServiceChange(event.target.value)}
            >
              {services.map((service) => (
                <option key={service.id} value={service.id}>
                  {service.name}
                </option>
              ))}
            </select>
            {canEdit ? (
              <>
                <button type="button" className="service-admin-button" onClick={addStage}>
                  Add Stage
                </button>
                <button
                  type="button"
                  className="service-admin-button service-admin-button-primary"
                  disabled={saving}
                  onClick={saveWorkflow}
                >
                  {saving ? 'Saving...' : 'Save Workflow'}
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  className="service-admin-button"
                  disabled
                  title="You do not have permission to edit workflows"
                >
                  <AccessLockIcon show />
                  Add Stage
                </button>
                <button
                  type="button"
                  className="service-admin-button service-admin-button-primary"
                  disabled
                  title="You do not have permission to edit workflows"
                >
                  <AccessLockIcon show />
                  Save Workflow
                </button>
              </>
            )}
          </div>
        </div>

        <div className="service-admin-table-wrap" style={{ marginTop: 12 }}>
          <table className="service-admin-table service-admin-workflow-table">
            <thead>
              <tr>
                <th>Stage</th>
                <th>Owner</th>
                <th>SLA</th>
                <th>Approval</th>
                <th>Evidence</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {stages.map((stage, index) => (
                <tr key={stage.id}>
                  <td>
                    <b>{stage.name}</b>
                  </td>
                  <td>{stage.ownerRole}</td>
                  <td>{hoursToDays(stage.slaHours)} day(s)</td>
                  <td>{stage.requiresApproval ? 'Yes' : 'No'}</td>
                  <td>{stage.requiresEvidence ? 'Required' : 'Optional'}</td>
                  <td>
                    {canEdit ? (
                      <div className="service-admin-acts">
                        <button
                          type="button"
                          className="service-admin-button service-admin-button-small"
                          onClick={() => openEdit(index)}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="service-admin-button service-admin-button-small"
                          onClick={() => deleteStage(index)}
                        >
                          Delete
                        </button>
                      </div>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="service-admin-g2">
        <AutomationRulesPanel />

        <div className="service-admin-card">
          <div className="service-admin-card-header">
            <div className="service-admin-card-title">Fulfillment Modes</div>
          </div>
          {fulfillmentModes.map(([title, description]) => (
            <div key={title} className="service-admin-list-row">
              <div className="service-admin-list-ico service-admin-list-ico--mode">
                <IconSubtask size={16} aria-hidden="true" />
              </div>
              <div className="service-admin-list-meta">
                <div className="service-admin-list-name">{title}</div>
                <div className="service-admin-list-sub">{description}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {canEdit && editingIndex !== null && stageDraft ? (
        <div
          className="service-admin-editor-backdrop"
          role="presentation"
          onMouseDown={() => {
            setEditingIndex(null)
            setStageDraft(null)
          }}
        >
          <section
            className="service-admin-field-editor-modal service-admin-stage-editor-modal"
            role="dialog"
            aria-modal="true"
            aria-label="Edit workflow stage"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <header>
              <div>
                <h2>Edit Stage</h2>
                <p>Update stage ownership, SLA and checkpoints</p>
              </div>
              <button
                type="button"
                className="service-admin-stage-editor-close"
                aria-label="Close"
                onClick={() => {
                  setEditingIndex(null)
                  setStageDraft(null)
                }}
              >
                ×
              </button>
            </header>
            <div className="service-admin-field-editor-body service-admin-stage-editor-body">
              <label className="service-admin-stage-editor-field service-admin-stage-editor-field--full">
                <span>Stage name</span>
                <input
                  value={stageDraft.name}
                  onChange={(event) =>
                    setStageDraft((current) =>
                      current ? { ...current, name: event.target.value } : current,
                    )
                  }
                />
              </label>
              <label className="service-admin-stage-editor-field">
                <span>Owner role</span>
                <select
                  value={stageDraft.ownerRoleId ?? ''}
                  disabled={ownerRoles.length === 0}
                  onChange={(event) => {
                    const roleId = event.target.value ? Number(event.target.value) : null
                    const role = ownerRoles.find((item) => item.id === roleId)
                    setStageDraft((current) =>
                      current
                        ? {
                            ...current,
                            ownerRoleId: role?.id ?? null,
                            ownerRole: role?.name ?? 'Unassigned',
                          }
                        : current,
                    )
                  }}
                >
                  <option value="">Unassigned</option>
                  {ownerRoles.map((role) => (
                    <option key={role.id} value={role.id}>
                      {role.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="service-admin-stage-editor-field">
                <span>SLA (days)</span>
                <input
                  type="number"
                  min={1}
                  value={formatNumberFieldValue(stageDraft.slaDays)}
                  onChange={(event) =>
                    setStageDraft((current) =>
                      current
                        ? { ...current, slaDays: parseNumberFieldValue(event.target.value) }
                        : current,
                    )
                  }
                />
              </label>
              <div className="service-admin-stage-editor-checks">
                <span className="service-admin-stage-editor-checks-label">Checkpoints</span>
                <div className="service-admin-stage-editor-check-grid">
                  <label className="service-admin-stage-editor-check">
                    <input
                      type="checkbox"
                      checked={stageDraft.requiresApproval}
                      onChange={(event) =>
                        setStageDraft((current) =>
                          current
                            ? { ...current, requiresApproval: event.target.checked }
                            : current,
                        )
                      }
                    />
                    <span>
                      <b>Requires approval</b>
                      <small>Stage cannot advance without sign-off</small>
                    </span>
                  </label>
                  <label className="service-admin-stage-editor-check">
                    <input
                      type="checkbox"
                      checked={stageDraft.requiresEvidence}
                      onChange={(event) =>
                        setStageDraft((current) =>
                          current
                            ? { ...current, requiresEvidence: event.target.checked }
                            : current,
                        )
                      }
                    />
                    <span>
                      <b>Evidence required</b>
                      <small>Upload or attach proof before completion</small>
                    </span>
                  </label>
                </div>
              </div>
            </div>
            <footer>
              <button
                type="button"
                className="service-admin-button"
                onClick={() => {
                  setEditingIndex(null)
                  setStageDraft(null)
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="service-admin-button service-admin-button-primary"
                onClick={applyStageEdit}
              >
                Save Stage
              </button>
            </footer>
          </section>
        </div>
      ) : null}
    </div>
  )
}
