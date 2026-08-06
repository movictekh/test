import {
  IconArrowDown,
  IconArrowUp,
  IconCalculator,
  IconClipboardText,
  IconGitBranch,
  IconPlus,
  IconTrash,
  IconX,
} from '@tabler/icons-react'
import { useMemo, useState, type ReactNode } from 'react'

import type {
  CalculatorCharge,
  CalculatorVariable,
  PricingCalculator,
  RequestFormField,
  SaveCalculatorInput,
  SaveRequestFormInput,
  SaveWorkflowInput,
  ServiceCatalogueItem,
  ServiceRequestForm,
  ServiceWorkflow,
  WorkflowStage,
} from '../types/service-administration.types'

type WorkflowControlKey = 'requiresEvidence' | 'requiresApproval' | 'clientVisible'

function Modal({
  title,
  subtitle,
  icon,
  children,
  onClose,
  onSave,
  saving,
  saveLabel = 'Save',
}: {
  title: string
  subtitle: string
  icon: ReactNode
  children: ReactNode
  onClose: () => void
  onSave: () => void
  saving: boolean
  saveLabel?: string
}) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/55 p-1 sm:p-4">
      <section className="bg-surface flex max-h-[98vh] w-full max-w-5xl flex-col overflow-hidden rounded-xl shadow-2xl sm:max-h-[92vh] sm:rounded-2xl">
        <header className="border-border flex items-start justify-between gap-4 border-b px-4 py-3">
          <div className="flex gap-2.5">
            <span className="bg-brand-50 text-brand-700 grid size-9 place-items-center rounded-xl">
              {icon}
            </span>
            <div>
              <h2 className="text-sm font-extrabold">{title}</h2>
              <p className="text-foreground-subtle mt-0.5 text-[0.625rem]">{subtitle}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="hover:bg-surface-muted grid size-8 place-items-center rounded-lg"
          >
            <IconX size={16} />
          </button>
        </header>
        <div className="flex-1 overflow-auto p-4">{children}</div>
        <footer className="border-border flex justify-end gap-2 border-t p-3">
          <button
            type="button"
            onClick={onClose}
            className="border-border rounded-control h-8 border px-3 text-[0.6875rem] font-semibold"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onSave}
            disabled={saving}
            className="bg-brand-600 rounded-control h-8 px-3 text-[0.6875rem] font-semibold text-white disabled:opacity-50"
          >
            {saving ? 'Saving…' : saveLabel}
          </button>
        </footer>
      </section>
    </div>
  )
}

function Input({
  label,
  value,
  onChange,
}: {
  label: string
  value: string | number
  onChange: (value: string) => void
}) {
  return (
    <label className="space-y-1">
      <span className="text-[0.625rem] font-bold">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="border-border rounded-control focus:border-brand-600 h-9 w-full border px-3 text-xs outline-none"
      />
    </label>
  )
}

function Select({
  label,
  value,
  onChange,
  children,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  children: ReactNode
}) {
  return (
    <label className="space-y-1">
      <span className="text-[0.625rem] font-bold">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="border-border rounded-control h-9 w-full border px-3 text-xs"
      >
        {children}
      </select>
    </label>
  )
}

export function CalculatorEditor({
  calculator,
  services,
  onClose,
  onSave,
  saving,
}: {
  calculator?: PricingCalculator
  services: ServiceCatalogueItem[]
  onClose: () => void
  onSave: (input: SaveCalculatorInput) => void
  saving: boolean
}) {
  const [name, setName] = useState(calculator?.name ?? '')
  const [code, setCode] = useState(calculator?.code ?? '')
  const [serviceId, setServiceId] = useState(calculator?.serviceId ?? services[0]?.id ?? '')
  const [description, setDescription] = useState(calculator?.description ?? '')
  const [status, setStatus] = useState(calculator?.status ?? 'draft')
  const [variables, setVariables] = useState<CalculatorVariable[]>(calculator?.variables ?? [])
  const [charges, setCharges] = useState<CalculatorCharge[]>(calculator?.charges ?? [])
  const [sampleTotal, setSampleTotal] = useState(calculator?.sampleTotal ?? 0)

  return (
    <Modal
      title={calculator ? `Edit ${calculator.name}` : 'Create Pricing Calculator'}
      subtitle="Variables, formula charges, deposit and preview data follow the prototype calculator workspace."
      icon={<IconCalculator size={18} />}
      onClose={onClose}
      saving={saving}
      onSave={() =>
        onSave({
          ...(calculator?.id ? { id: calculator.id } : {}),
          name,
          code,
          serviceId,
          description,
          status,
          variables,
          charges,
          sampleTotal: Number(sampleTotal),
        })
      }
    >
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Input label="Calculator name" value={name} onChange={setName} />
            <Input label="Code" value={code} onChange={setCode} />
            <Select label="Service" value={serviceId} onChange={setServiceId}>
              {services.map((service) => (
                <option key={service.id} value={service.id}>
                  {service.name}
                </option>
              ))}
            </Select>
            <Select
              label="Status"
              value={status}
              onChange={(value) => setStatus(value as typeof status)}
            >
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </Select>
          </div>

          <label className="space-y-1">
            <span className="text-[0.625rem] font-bold">Description</span>
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={3}
              className="border-border rounded-control w-full border p-3 text-xs"
            />
          </label>

          <BuilderSection
            title="Variables"
            onAdd={() =>
              setVariables((current) => [
                ...current,
                {
                  id: `variable-${Date.now()}`,
                  label: 'New variable',
                  key: `variable_${current.length + 1}`,
                  type: 'number',
                },
              ])
            }
          >
            {variables.map((variable, index) => (
              <div
                key={variable.id}
                className="border-border grid gap-2 rounded-lg border p-2.5 sm:grid-cols-[1fr_1fr_110px_80px_auto]"
              >
                <Input
                  label="Label"
                  value={variable.label}
                  onChange={(value) =>
                    setVariables((current) =>
                      current.map((item, itemIndex) =>
                        itemIndex === index ? { ...item, label: value } : item,
                      ),
                    )
                  }
                />
                <Input
                  label="Key"
                  value={variable.key}
                  onChange={(value) =>
                    setVariables((current) =>
                      current.map((item, itemIndex) =>
                        itemIndex === index ? { ...item, key: value } : item,
                      ),
                    )
                  }
                />
                <Select
                  label="Type"
                  value={variable.type}
                  onChange={(value) =>
                    setVariables((current) =>
                      current.map((item, itemIndex) =>
                        itemIndex === index
                          ? { ...item, type: value as CalculatorVariable['type'] }
                          : item,
                      ),
                    )
                  }
                >
                  <option value="number">Number</option>
                  <option value="select">Select</option>
                  <option value="boolean">Boolean</option>
                </Select>
                <Input
                  label="Unit"
                  value={variable.unit ?? ''}
                  onChange={(value) =>
                    setVariables((current) =>
                      current.map((item, itemIndex) =>
                        itemIndex === index ? { ...item, unit: value } : item,
                      ),
                    )
                  }
                />
                <button
                  type="button"
                  onClick={() =>
                    setVariables((current) => current.filter((_, itemIndex) => itemIndex !== index))
                  }
                  className="text-danger-700 self-end pb-2"
                >
                  <IconTrash size={15} />
                </button>
              </div>
            ))}
          </BuilderSection>

          <BuilderSection
            title="Charges and formula lines"
            onAdd={() =>
              setCharges((current) => [
                ...current,
                {
                  id: `charge-${Date.now()}`,
                  label: 'New charge',
                  kind: 'fixed',
                  value: 0,
                },
              ])
            }
          >
            {charges.map((charge, index) => (
              <div
                key={charge.id}
                className="border-border grid gap-2 rounded-lg border p-2.5 sm:grid-cols-[1fr_130px_1fr_auto]"
              >
                <Input
                  label="Label"
                  value={charge.label}
                  onChange={(value) =>
                    setCharges((current) =>
                      current.map((item, itemIndex) =>
                        itemIndex === index ? { ...item, label: value } : item,
                      ),
                    )
                  }
                />
                <Select
                  label="Kind"
                  value={charge.kind}
                  onChange={(value) =>
                    setCharges((current) =>
                      current.map((item, itemIndex) =>
                        itemIndex === index
                          ? { ...item, kind: value as CalculatorCharge['kind'] }
                          : item,
                      ),
                    )
                  }
                >
                  <option value="fixed">Fixed</option>
                  <option value="percentage">Percentage</option>
                  <option value="formula">Formula</option>
                </Select>
                <Input
                  label="Value / expression"
                  value={charge.value}
                  onChange={(value) =>
                    setCharges((current) =>
                      current.map((item, itemIndex) =>
                        itemIndex === index
                          ? { ...item, value: item.kind === 'formula' ? value : Number(value) }
                          : item,
                      ),
                    )
                  }
                />
                <button
                  type="button"
                  onClick={() =>
                    setCharges((current) => current.filter((_, itemIndex) => itemIndex !== index))
                  }
                  className="text-danger-700 self-end pb-2"
                >
                  <IconTrash size={15} />
                </button>
              </div>
            ))}
          </BuilderSection>
        </div>

        <aside className="border-border bg-surface-muted h-fit rounded-xl border p-3">
          <h3 className="text-[0.6875rem] font-extrabold">Calculator preview</h3>
          <p className="text-foreground-subtle mt-1 text-[0.5625rem]">
            The prototype preview uses a safe sample value; formula execution remains controlled.
          </p>
          <div className="mt-3 space-y-2">
            {variables.map((variable) => (
              <div
                key={variable.id}
                className="bg-surface border-border rounded-lg border p-2 text-[0.625rem]"
              >
                <span className="font-semibold">{variable.label}</span>
                <span className="text-foreground-subtle float-right">{variable.type}</span>
              </div>
            ))}
          </div>
          <div className="mt-3">
            <Input
              label="Sample total"
              value={sampleTotal}
              onChange={(value) => setSampleTotal(Number(value))}
            />
          </div>
          <div className="bg-brand-600 mt-3 rounded-xl p-3 text-white">
            <p className="text-[0.5625rem] uppercase opacity-70">Preview estimate</p>
            <p className="mt-1 text-xl font-extrabold">
              {new Intl.NumberFormat('en-NG', {
                style: 'currency',
                currency: 'NGN',
                maximumFractionDigits: 0,
              }).format(Number(sampleTotal))}
            </p>
          </div>
        </aside>
      </div>
    </Modal>
  )
}

function BuilderSection({
  title,
  onAdd,
  children,
}: {
  title: string
  onAdd: () => void
  children: ReactNode
}) {
  return (
    <section>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-[0.6875rem] font-extrabold">{title}</h3>
        <button
          type="button"
          onClick={onAdd}
          className="border-border rounded-control inline-flex h-7 items-center gap-1 border px-2 text-[0.625rem] font-semibold"
        >
          <IconPlus size={13} />
          Add
        </button>
      </div>
      <div className="space-y-2">{children}</div>
    </section>
  )
}

const palette: Pick<RequestFormField, 'type' | 'label'>[] = [
  { type: 'text', label: 'Short text' },
  { type: 'textarea', label: 'Long text' },
  { type: 'number', label: 'Number' },
  { type: 'date', label: 'Date' },
  { type: 'select', label: 'Select' },
  { type: 'file', label: 'File upload' },
  { type: 'checkbox', label: 'Checkbox' },
]

export function RequestFormEditor({
  form,
  services,
  onClose,
  onSave,
  saving,
}: {
  form?: ServiceRequestForm
  services: ServiceCatalogueItem[]
  onClose: () => void
  onSave: (input: SaveRequestFormInput) => void
  saving: boolean
}) {
  const [name, setName] = useState(form?.name ?? '')
  const [serviceId, setServiceId] = useState(form?.serviceId ?? services[0]?.id ?? '')
  const [status, setStatus] = useState(form?.status ?? 'draft')
  const [fields, setFields] = useState<RequestFormField[]>(form?.fields ?? [])

  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction
    if (target < 0 || target >= fields.length) return
    setFields((current) => {
      const next = [...current]
      ;[next[index], next[target]] = [next[target]!, next[index]!]
      return next
    })
  }

  return (
    <Modal
      title={form ? `Edit ${form.name}` : 'Create Request Form'}
      subtitle="Palette and canvas follow the prototype builder layout."
      icon={<IconClipboardText size={18} />}
      onClose={onClose}
      saving={saving}
      onSave={() =>
        onSave({ ...(form?.id ? { id: form.id } : {}), name, serviceId, status, fields })
      }
    >
      <div className="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)]">
        <aside className="border-border bg-surface-muted rounded-xl border p-3">
          <h3 className="text-[0.6875rem] font-extrabold">Field palette</h3>
          <p className="text-foreground-subtle mt-1 text-[0.5625rem]">
            Add fields to the request canvas.
          </p>
          <div className="mt-3 space-y-1.5">
            {palette.map((item) => (
              <button
                key={item.type}
                type="button"
                onClick={() =>
                  setFields((current) => [
                    ...current,
                    {
                      id: `field-${Date.now()}`,
                      key: `field_${current.length + 1}`,
                      label: item.label,
                      type: item.type,
                      required: false,
                    },
                  ])
                }
                className="border-border bg-surface hover:border-brand-300 flex w-full items-center gap-2 rounded-lg border border-dashed px-2.5 py-2 text-left text-[0.625rem] font-semibold"
              >
                <IconPlus size={13} />
                {item.label}
              </button>
            ))}
          </div>
        </aside>

        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-3">
            <Input label="Form name" value={name} onChange={setName} />
            <Select label="Service" value={serviceId} onChange={setServiceId}>
              {services.map((service) => (
                <option key={service.id} value={service.id}>
                  {service.name}
                </option>
              ))}
            </Select>
            <Select
              label="Status"
              value={status}
              onChange={(value) => setStatus(value as typeof status)}
            >
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </Select>
          </div>

          <section className="border-border min-h-80 rounded-xl border p-3">
            <div className="mb-3">
              <h3 className="text-[0.6875rem] font-extrabold">Form canvas</h3>
              <p className="text-foreground-subtle mt-0.5 text-[0.5625rem]">
                {fields.length} configured fields
              </p>
            </div>
            <div className="space-y-2">
              {fields.map((field, index) => (
                <div
                  key={field.id}
                  className="border-border bg-surface-muted rounded-lg border p-2.5"
                >
                  <div className="grid gap-2 sm:grid-cols-[1fr_1fr_120px_auto]">
                    <Input
                      label="Label"
                      value={field.label}
                      onChange={(value) =>
                        setFields((current) =>
                          current.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, label: value } : item,
                          ),
                        )
                      }
                    />
                    <Input
                      label="Key"
                      value={field.key}
                      onChange={(value) =>
                        setFields((current) =>
                          current.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, key: value } : item,
                          ),
                        )
                      }
                    />
                    <Select
                      label="Type"
                      value={field.type}
                      onChange={(value) =>
                        setFields((current) =>
                          current.map((item, itemIndex) =>
                            itemIndex === index
                              ? { ...item, type: value as RequestFormField['type'] }
                              : item,
                          ),
                        )
                      }
                    >
                      {palette.map((item) => (
                        <option key={item.type} value={item.type}>
                          {item.label}
                        </option>
                      ))}
                    </Select>
                    <div className="flex items-end gap-1 pb-1">
                      <button
                        type="button"
                        onClick={() => move(index, -1)}
                        className="border-border grid size-7 place-items-center rounded border"
                      >
                        <IconArrowUp size={13} />
                      </button>
                      <button
                        type="button"
                        onClick={() => move(index, 1)}
                        className="border-border grid size-7 place-items-center rounded border"
                      >
                        <IconArrowDown size={13} />
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          setFields((current) =>
                            current.filter((_, itemIndex) => itemIndex !== index),
                          )
                        }
                        className="text-danger-700 border-border grid size-7 place-items-center rounded border"
                      >
                        <IconTrash size={13} />
                      </button>
                    </div>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-3">
                    <label className="flex items-center gap-1.5 text-[0.625rem] font-semibold">
                      <input
                        type="checkbox"
                        checked={field.required}
                        onChange={(event) =>
                          setFields((current) =>
                            current.map((item, itemIndex) =>
                              itemIndex === index
                                ? { ...item, required: event.target.checked }
                                : item,
                            ),
                          )
                        }
                      />
                      Required
                    </label>
                    <input
                      value={field.helpText ?? ''}
                      onChange={(event) =>
                        setFields((current) =>
                          current.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, helpText: event.target.value } : item,
                          ),
                        )
                      }
                      placeholder="Help text"
                      className="border-border rounded-control h-8 min-w-52 flex-1 border px-2.5 text-[0.625rem]"
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </Modal>
  )
}

export function WorkflowEditor({
  workflow,
  services,
  onClose,
  onSave,
  saving,
}: {
  workflow?: ServiceWorkflow
  services: ServiceCatalogueItem[]
  onClose: () => void
  onSave: (input: SaveWorkflowInput) => void
  saving: boolean
}) {
  const [name, setName] = useState(workflow?.name ?? '')
  const [serviceId, setServiceId] = useState(workflow?.serviceId ?? services[0]?.id ?? '')
  const [status, setStatus] = useState(workflow?.status ?? 'draft')
  const [stages, setStages] = useState<WorkflowStage[]>(workflow?.stages ?? [])
  const workflowControls: Array<[WorkflowControlKey, string]> = [
    ['requiresEvidence', 'Evidence required'],
    ['requiresApproval', 'Approval required'],
    ['clientVisible', 'Client visible'],
  ]

  const normalized = useMemo(
    () => stages.map((stage, index) => ({ ...stage, order: index + 1 })),
    [stages],
  )

  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction
    if (target < 0 || target >= stages.length) return
    setStages((current) => {
      const next = [...current]
      ;[next[index], next[target]] = [next[target]!, next[index]!]
      return next
    })
  }

  return (
    <Modal
      title={workflow ? `Edit ${workflow.name}` : 'Create Workflow'}
      subtitle="Stage sequence, ownership, SLA and controls match the prototype workflow designer."
      icon={<IconGitBranch size={18} />}
      onClose={onClose}
      saving={saving}
      onSave={() =>
        onSave({
          ...(workflow?.id ? { id: workflow.id } : {}),
          name,
          serviceId,
          status,
          stages: normalized,
        })
      }
    >
      <div className="grid gap-3 sm:grid-cols-3">
        <Input label="Workflow name" value={name} onChange={setName} />
        <Select label="Service" value={serviceId} onChange={setServiceId}>
          {services.map((service) => (
            <option key={service.id} value={service.id}>
              {service.name}
            </option>
          ))}
        </Select>
        <Select
          label="Status"
          value={status}
          onChange={(value) => setStatus(value as typeof status)}
        >
          <option value="draft">Draft</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </Select>
      </div>

      <section className="mt-4">
        <div className="mb-2 flex items-center justify-between">
          <div>
            <h3 className="text-[0.6875rem] font-extrabold">Workflow stages</h3>
            <p className="text-foreground-subtle mt-0.5 text-[0.5625rem]">
              Order the stages used during fulfilment.
            </p>
          </div>
          <button
            type="button"
            onClick={() =>
              setStages((current) => [
                ...current,
                {
                  id: `stage-${Date.now()}`,
                  name: 'New Stage',
                  order: current.length + 1,
                  ownerRole: 'Service Manager',
                  slaHours: 24,
                  requiresEvidence: false,
                  requiresApproval: false,
                  clientVisible: true,
                },
              ])
            }
            className="border-border rounded-control inline-flex h-7 items-center gap-1 border px-2 text-[0.625rem] font-semibold"
          >
            <IconPlus size={13} />
            Add Stage
          </button>
        </div>

        <div className="space-y-2">
          {normalized.map((stage, index) => (
            <div key={stage.id} className="border-border rounded-xl border p-3">
              <div className="grid gap-2 lg:grid-cols-[44px_1fr_1fr_100px_auto]">
                <div className="bg-brand-600 grid size-9 place-items-center self-end rounded-full text-xs font-extrabold text-white">
                  {index + 1}
                </div>
                <Input
                  label="Stage name"
                  value={stage.name}
                  onChange={(value) =>
                    setStages((current) =>
                      current.map((item, itemIndex) =>
                        itemIndex === index ? { ...item, name: value } : item,
                      ),
                    )
                  }
                />
                <Input
                  label="Owner role"
                  value={stage.ownerRole}
                  onChange={(value) =>
                    setStages((current) =>
                      current.map((item, itemIndex) =>
                        itemIndex === index ? { ...item, ownerRole: value } : item,
                      ),
                    )
                  }
                />
                <Input
                  label="SLA hours"
                  value={stage.slaHours}
                  onChange={(value) =>
                    setStages((current) =>
                      current.map((item, itemIndex) =>
                        itemIndex === index ? { ...item, slaHours: Number(value) } : item,
                      ),
                    )
                  }
                />
                <div className="flex items-end gap-1 pb-1">
                  <button
                    type="button"
                    onClick={() => move(index, -1)}
                    className="border-border grid size-7 place-items-center rounded border"
                  >
                    <IconArrowUp size={13} />
                  </button>
                  <button
                    type="button"
                    onClick={() => move(index, 1)}
                    className="border-border grid size-7 place-items-center rounded border"
                  >
                    <IconArrowDown size={13} />
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      setStages((current) => current.filter((_, itemIndex) => itemIndex !== index))
                    }
                    className="text-danger-700 border-border grid size-7 place-items-center rounded border"
                  >
                    <IconTrash size={13} />
                  </button>
                </div>
              </div>
              <div className="mt-2 flex flex-wrap gap-3">
                {workflowControls.map(([key, label]) => (
                  <label
                    key={key}
                    className="flex items-center gap-1.5 text-[0.625rem] font-semibold"
                  >
                    <input
                      type="checkbox"
                      checked={Boolean(stage[key as keyof WorkflowStage])}
                      onChange={(event) =>
                        setStages((current) =>
                          current.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, [key]: event.target.checked } : item,
                          ),
                        )
                      }
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </Modal>
  )
}
