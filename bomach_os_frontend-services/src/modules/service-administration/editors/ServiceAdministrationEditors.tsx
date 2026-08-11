import { IconX } from '@tabler/icons-react'
import { useMemo, useState, type ReactNode } from 'react'

import { formatNumberFieldValue, parseNumberFieldValue } from '@/shared/lib/number-input'

import type {
  CalculatorCharge,
  CalculatorVariable,
  PricingCalculator,
  PricingType,
  RequestFormField,
  SaveCalculatorInput,
  SaveRequestFormInput,
  SaveWorkflowInput,
  ServiceCatalogueItem,
  ServiceRequestForm,
  ServiceWorkflow,
  WorkflowStage,
} from '../types/service-administration.types'

function EditorModal({
  title,
  children,
  onClose,
  onSave,
  saving,
  saveLabel,
  saveDisabled = false,
}: {
  title: string
  children: ReactNode
  onClose: () => void
  onSave: () => void
  saving: boolean
  saveLabel: string
  saveDisabled?: boolean
}) {
  return (
    <div className="service-admin-editor-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="service-admin-editor-modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="service-admin-editor-header">
          <h2>{title}</h2>
          <button type="button" className="service-admin-editor-close" onClick={onClose}>
            <IconX size={15} />
          </button>
        </header>
        <div className="service-admin-editor-body">{children}</div>
        <footer className="service-admin-editor-footer">
          <button type="button" className="service-admin-button" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="service-admin-button service-admin-button-primary"
            disabled={saving || saveDisabled}
            onClick={onSave}
          >
            {saving ? 'Saving…' : saveLabel}
          </button>
        </footer>
      </section>
    </div>
  )
}

function EditorField({
  label,
  children,
  full = false,
}: {
  label: string
  children: ReactNode
  full?: boolean
}) {
  return (
    <label
      className={`service-admin-editor-field ${full ? 'service-admin-editor-field--full' : ''}`}
    >
      <span>{label}</span>
      {children}
    </label>
  )
}

const pricingTemplateOptions: Array<{ value: PricingType; label: string }> = [
  { value: 'fixed', label: 'Fixed' },
  { value: 'unit_rate', label: 'Unit rate' },
  { value: 'area_rate', label: 'Area rate' },
  { value: 'percentage', label: 'Percentage' },
  { value: 'formula', label: 'Custom formula' },
]

function percentageCharge(
  calculator: PricingCalculator | undefined,
  keyword: string,
  fallback: number,
) {
  const value = calculator?.charges.find((charge) =>
    charge.label.toLowerCase().includes(keyword),
  )?.value
  return typeof value === 'number' ? value : fallback
}

function isValidPercentage(value: number) {
  return Number.isFinite(value) && value >= 0 && value <= 100
}

function serializeVariables(variables: CalculatorVariable[]) {
  return variables.map((item) => `${item.key}|${item.label}|${item.unit ?? ''}`).join('\n')
}

function parseVariables(value: string): CalculatorVariable[] {
  return value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const [key = `field_${index + 1}`, label = `Field ${index + 1}`, unit = ''] = line
        .split('|')
        .map((part) => part.trim())
      return {
        id: `variable-${Date.now()}-${index}`,
        key,
        label,
        type: 'number' as const,
        ...(unit ? { unit } : {}),
      }
    })
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
  const [serviceId, setServiceId] = useState(calculator?.serviceId ?? '')
  const [pricingType, setPricingType] = useState<PricingType>(calculator?.pricingType ?? 'fixed')
  const [status, setStatus] = useState(calculator?.status ?? 'draft')
  const [formula, setFormula] = useState(
    String(
      calculator?.charges.find((charge) => charge.kind === 'formula')?.value ??
        'quantity * unit_rate + logistics',
    ),
  )
  const [deposit, setDeposit] = useState(percentageCharge(calculator, 'deposit', 70))
  const [tax, setTax] = useState(percentageCharge(calculator, 'tax', 0))
  const [fieldsText, setFieldsText] = useState(
    calculator?.variables.length
      ? serializeVariables(calculator.variables)
      : 'quantity|Quantity|1\nunit_rate|Unit rate|100000\nlogistics|Logistics|0',
  )

  const service = services.find((item) => item.id === serviceId)
  const hasValidService = Boolean(serviceId && Number(serviceId) > 0 && service)
  const canSave = Boolean(
    name.trim() &&
    hasValidService &&
    isValidPercentage(Number(deposit)) &&
    isValidPercentage(Number(tax)),
  )

  return (
    <EditorModal
      title={calculator ? `Edit ${calculator.name}` : 'Create Service Calculator'}
      onClose={onClose}
      saving={saving}
      saveDisabled={!canSave}
      saveLabel={calculator ? 'Save Calculator' : 'Create Calculator'}
      onSave={() => {
        if (!canSave) return

        const charges: CalculatorCharge[] = [
          ...(pricingType === 'formula'
            ? [
                {
                  id:
                    calculator?.charges.find((charge) => charge.kind === 'formula')?.id ??
                    `formula-${Date.now()}`,
                  label: 'Formula',
                  kind: 'formula' as const,
                  value: formula,
                },
              ]
            : []),
          {
            id:
              calculator?.charges.find((charge) => charge.label.toLowerCase().includes('deposit'))
                ?.id ?? `deposit-${Date.now()}`,
            label: 'Deposit',
            kind: 'percentage',
            value: Number(deposit),
          },
          {
            id:
              calculator?.charges.find((charge) => charge.label.toLowerCase().includes('tax'))
                ?.id ?? `tax-${Date.now()}`,
            label: 'Tax',
            kind: 'percentage',
            value: Number(tax),
          },
        ]

        onSave({
          ...(calculator?.id ? { id: calculator.id } : {}),
          name: name.trim(),
          code: calculator?.code ?? `CALC-${service?.code ?? 'NEW'}-01`,
          serviceId,
          description: `${
            pricingTemplateOptions.find((item) => item.value === pricingType)?.label ?? 'Pricing'
          } calculator for ${service?.name ?? 'service pricing'}.`,
          pricingType,
          status,
          variables: parseVariables(fieldsText),
          charges,
          sampleTotal: calculator?.sampleTotal ?? 0,
        })
      }}
    >
      <div className="service-admin-editor-grid">
        <EditorField label="Name">
          <input value={name} required onChange={(event) => setName(event.target.value)} />
        </EditorField>
        <EditorField label="Service">
          <select
            value={serviceId}
            required
            aria-required="true"
            disabled={services.length === 0}
            onChange={(event) => setServiceId(event.target.value)}
          >
            {services.length === 0 ? (
              <option value="">Create a service first</option>
            ) : (
              <>
                {!calculator ? <option value="">Select a service</option> : null}
                {services.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </>
            )}
          </select>
        </EditorField>
        <EditorField label="Template">
          <select
            value={pricingType}
            onChange={(event) => setPricingType(event.target.value as PricingType)}
          >
            {pricingTemplateOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </EditorField>
        <EditorField label="Status">
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value as typeof status)}
          >
            <option value="draft">Draft</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </EditorField>
        <EditorField label="Formula">
          <input
            value={formula}
            disabled={pricingType !== 'formula'}
            onChange={(event) => setFormula(event.target.value)}
          />
        </EditorField>
        <EditorField label="Deposit (%)">
          <input
            type="number"
            min={0}
            max={100}
            value={formatNumberFieldValue(deposit)}
            onChange={(event) => setDeposit(parseNumberFieldValue(event.target.value))}
          />
        </EditorField>
        <EditorField label="Tax (%)">
          <input
            type="number"
            min={0}
            max={100}
            value={formatNumberFieldValue(tax)}
            onChange={(event) => setTax(parseNumberFieldValue(event.target.value))}
          />
        </EditorField>
        {!isValidPercentage(Number(deposit)) || !isValidPercentage(Number(tax)) ? (
          <EditorField label="Validation" full>
            <div className="service-admin-notice service-admin-notice-yellow">
              Deposit and Tax must both be between 0 and 100.
            </div>
          </EditorField>
        ) : null}
        <EditorField label="Fields — variable|Label|default, one per line" full>
          <textarea value={fieldsText} onChange={(event) => setFieldsText(event.target.value)} />
        </EditorField>
      </div>
    </EditorModal>
  )
}

const requestFieldTypes: RequestFormField['type'][] = [
  'text',
  'textarea',
  'number',
  'date',
  'select',
  'file',
  'checkbox',
]

function serializeRequestFields(fields: RequestFormField[]) {
  return fields
    .map(
      (field) =>
        `${field.label}|${field.type}|${field.required ? 'required' : 'optional'}|${field.options?.join(',') ?? ''}`,
    )
    .join('\n')
}

function parseRequestFields(value: string): RequestFormField[] {
  return value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const [label = `Field ${index + 1}`, rawType = 'text', required = 'optional', options = ''] =
        line.split('|').map((part) => part.trim())
      const type = requestFieldTypes.includes(rawType as RequestFormField['type'])
        ? (rawType as RequestFormField['type'])
        : 'text'
      return {
        id: `field-${Date.now()}-${index}`,
        label,
        key: label
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, '_')
          .replace(/^_|_$/g, ''),
        type,
        required: required.toLowerCase() === 'required',
        ...(options
          ? {
              options: options
                .split(',')
                .map((item) => item.trim())
                .filter(Boolean),
            }
          : {}),
      }
    })
}

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
  const [fieldsText, setFieldsText] = useState(
    form?.fields.length
      ? serializeRequestFields(form.fields)
      : 'Full name|text|required|\nPhone|text|required|\nEmail|text|required|',
  )

  return (
    <EditorModal
      title={form ? `Edit ${form.name}` : 'Create Request Form'}
      onClose={onClose}
      saving={saving}
      saveLabel={form ? 'Save Form' : 'Create Form'}
      onSave={() =>
        onSave({
          ...(form?.id ? { id: form.id } : {}),
          name,
          serviceId,
          status,
          fields: parseRequestFields(fieldsText),
        })
      }
    >
      <div className="service-admin-editor-grid">
        <EditorField label="Form name">
          <input value={name} onChange={(event) => setName(event.target.value)} />
        </EditorField>
        <EditorField label="Service">
          <select value={serviceId} onChange={(event) => setServiceId(event.target.value)}>
            {services.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </EditorField>
        <EditorField label="Status">
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value as typeof status)}
          >
            <option value="draft">Draft</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </EditorField>
        <EditorField label="Fields — Label|type|required|options, one per line" full>
          <textarea value={fieldsText} onChange={(event) => setFieldsText(event.target.value)} />
        </EditorField>
      </div>
    </EditorModal>
  )
}

function serializeStages(stages: WorkflowStage[]) {
  return stages
    .slice()
    .sort((a, b) => a.order - b.order)
    .map(
      (stage) =>
        `${stage.name}|${stage.ownerRole}|${stage.slaHours}|${stage.requiresEvidence ? 'evidence' : ''}|${stage.requiresApproval ? 'approval' : ''}|${stage.clientVisible ? 'visible' : 'hidden'}`,
    )
    .join('\n')
}

function parseStages(value: string): WorkflowStage[] {
  return value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const [
        name = `Stage ${index + 1}`,
        ownerRole = 'Service Manager',
        slaHours = '24',
        evidence = '',
        approval = '',
        visibility = 'visible',
      ] = line.split('|').map((part) => part.trim())
      return {
        id: `stage-${Date.now()}-${index}`,
        name,
        order: index + 1,
        ownerRole,
        slaHours: Number(slaHours) || 24,
        requiresEvidence: evidence.toLowerCase() === 'evidence',
        requiresApproval: approval.toLowerCase() === 'approval',
        clientVisible: visibility.toLowerCase() !== 'hidden',
      }
    })
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
  const [stagesText, setStagesText] = useState(
    workflow?.stages.length
      ? serializeStages(workflow.stages)
      : 'Request Review|Service Administrator|4||approval|visible\nExecution|Service Manager|24|evidence||visible\nCompletion|Head of Operations|8|evidence|approval|visible',
  )
  const preview = useMemo(() => parseStages(stagesText), [stagesText])

  return (
    <EditorModal
      title={workflow ? `Edit ${workflow.name}` : 'Create Service Workflow'}
      onClose={onClose}
      saving={saving}
      saveLabel={workflow ? 'Save Workflow' : 'Create Workflow'}
      onSave={() =>
        onSave({
          ...(workflow?.id ? { id: workflow.id } : {}),
          name,
          serviceId,
          status,
          stages: parseStages(stagesText),
        })
      }
    >
      <div className="service-admin-editor-grid">
        <EditorField label="Workflow name">
          <input value={name} onChange={(event) => setName(event.target.value)} />
        </EditorField>
        <EditorField label="Service">
          <select value={serviceId} onChange={(event) => setServiceId(event.target.value)}>
            {services.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </EditorField>
        <EditorField label="Status">
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value as typeof status)}
          >
            <option value="draft">Draft</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </EditorField>
        <EditorField
          label="Stages — Name|Owner|SLA hours|evidence|approval|visible, one per line"
          full
        >
          <textarea value={stagesText} onChange={(event) => setStagesText(event.target.value)} />
        </EditorField>
      </div>
      <div className="service-admin-editor-stage-preview">
        {preview.map((stage) => (
          <div key={stage.id}>
            <small>{String(stage.order).padStart(2, '0')}</small>
            <b>{stage.name}</b>
            <span>{stage.ownerRole}</span>
          </div>
        ))}
      </div>
    </EditorModal>
  )
}
