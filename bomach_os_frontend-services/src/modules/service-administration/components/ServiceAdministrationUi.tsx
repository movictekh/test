import {
  IconBuilding,
  IconCalculator,
  IconChevronRight,
  IconClipboardText,
  IconGitBranch,
  IconPlus,
  IconSettings,
} from '@tabler/icons-react'
import { useMemo, useState, type ReactNode } from 'react'

import { cn } from '@/shared/lib/cn'
import { formatCurrency } from '@/shared/lib/formatters'
import { CompactActionButton } from '@/shared/ui/module-controls'

import type {
  BranchActivation,
  ConfigurationStatus,
  PricingCalculator,
  ServiceCatalogueItem,
  ServiceRequestForm,
  ServiceWorkflow,
} from '../types/service-administration.types'

export function StatusPill({ status }: { status: ConfigurationStatus | 'setup-required' }) {
  const label = status.replaceAll('-', ' ')
  return (
    <span
      className={cn(
        'inline-flex rounded-full px-2 py-0.5 text-[0.5625rem] font-bold capitalize',
        status === 'active' && 'bg-success-50 text-success-700',
        status === 'draft' && 'bg-warning-50 text-warning-700',
        status === 'inactive' && 'bg-surface-muted text-foreground-subtle',
        status === 'setup-required' && 'bg-danger-50 text-danger-700',
      )}
    >
      {label}
    </span>
  )
}

export function SectionCard({
  title,
  description,
  icon,
  action,
  children,
}: {
  title: string
  description?: string
  icon?: ReactNode
  action?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="border-border bg-surface rounded-card border">
      <header className="border-border flex items-start justify-between gap-3 border-b px-3 py-2.5">
        <div className="flex min-w-0 items-start gap-2">
          {icon ? (
            <span className="bg-brand-50 text-brand-700 grid size-7 shrink-0 place-items-center rounded-lg">
              {icon}
            </span>
          ) : null}
          <div>
            <h2 className="text-foreground text-[0.6875rem] font-extrabold">{title}</h2>
            {description ? (
              <p className="text-foreground-subtle mt-0.5 text-[0.5625rem]">{description}</p>
            ) : null}
          </div>
        </div>
        {action}
      </header>
      {children}
    </section>
  )
}

export function ServiceCatalogueGrid({
  services,
  onSelect,
}: {
  services: ServiceCatalogueItem[]
  onSelect: (item: ServiceCatalogueItem) => void
}) {
  return (
    <div className="grid gap-2.5 lg:grid-cols-2 2xl:grid-cols-3">
      {services.map((service) => (
        <button
          type="button"
          key={service.id}
          onClick={() => onSelect(service)}
          className="border-border bg-surface hover:border-brand-300 rounded-card border p-3 text-left transition-colors"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-start gap-2.5">
              <span className="bg-brand-50 text-brand-700 grid size-9 shrink-0 place-items-center rounded-xl">
                <IconBuilding size={18} />
              </span>
              <div className="min-w-0">
                <p className="text-foreground truncate text-[0.6875rem] font-extrabold">
                  {service.name}
                </p>
                <p className="text-foreground-subtle mt-0.5 text-[0.5625rem]">
                  {service.code} · {service.division}
                </p>
              </div>
            </div>
            <StatusPill status={service.status} />
          </div>
          <p className="text-foreground-subtle mt-2 line-clamp-2 text-[0.625rem] leading-4">
            {service.description}
          </p>
          <div className="mt-2.5 grid grid-cols-3 gap-1.5 text-center">
            <div className="bg-surface-muted rounded-lg p-1.5">
              <p className="text-foreground text-[0.6875rem] font-extrabold">
                {service.branchNames.length}
              </p>
              <p className="text-foreground-subtle text-[0.5rem] uppercase">Branches</p>
            </div>
            <div className="bg-surface-muted rounded-lg p-1.5">
              <p className="text-foreground text-[0.6875rem] font-extrabold">
                {service.subserviceCount}
              </p>
              <p className="text-foreground-subtle text-[0.5rem] uppercase">Subservices</p>
            </div>
            <div className="bg-surface-muted rounded-lg p-1.5">
              <p className="text-foreground text-[0.6875rem] font-extrabold">
                {service.readiness}%
              </p>
              <p className="text-foreground-subtle text-[0.5rem] uppercase">Ready</p>
            </div>
          </div>
          <div className="mt-2.5 flex items-center justify-between">
            <span className="text-foreground-subtle text-[0.5625rem]">{service.owner}</span>
            <IconChevronRight size={14} className="text-brand-700" />
          </div>
        </button>
      ))}
    </div>
  )
}

export function ServiceDetailPanel({
  service,
  onClose,
}: {
  service: ServiceCatalogueItem
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30" onMouseDown={onClose}>
      <aside
        className="bg-surface h-full w-full max-w-md overflow-y-auto shadow-2xl"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="border-border bg-surface sticky top-0 flex items-start justify-between border-b p-4">
          <div>
            <p className="text-brand-700 text-[0.5625rem] font-bold tracking-[0.1em] uppercase">
              Service profile
            </p>
            <h2 className="text-foreground mt-1 text-base font-extrabold">{service.name}</h2>
            <p className="text-foreground-subtle text-[0.625rem]">
              {service.code} · {service.division}
            </p>
          </div>
          <CompactActionButton onClick={onClose} tone="ghost">
            Close
          </CompactActionButton>
        </header>
        <div className="space-y-4 p-4">
          <p className="text-foreground-subtle text-xs leading-5">{service.description}</p>
          <div className="grid grid-cols-2 gap-2">
            {[
              ['Status', service.status],
              ['Owner', service.owner],
              ['Readiness', `${service.readiness}%`],
              ['Subservices', service.subserviceCount],
            ].map(([label, value]) => (
              <div key={label} className="bg-surface-muted rounded-xl p-3">
                <p className="text-foreground-subtle text-[0.5625rem] font-bold uppercase">
                  {label}
                </p>
                <p className="text-foreground mt-1 text-xs font-bold capitalize">{value}</p>
              </div>
            ))}
          </div>
          <SectionCard title="Configuration links" icon={<IconSettings size={14} />}>
            <div className="divide-border divide-y px-3">
              {[
                ['Calculator', service.calculatorName ?? 'Not configured'],
                ['Request form', service.requestFormName ?? 'Not configured'],
                ['Workflow', service.workflowName ?? 'Not configured'],
                ['Branches', service.branchNames.join(', ') || 'No active branch'],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="flex items-start justify-between gap-3 py-2.5 text-[0.625rem]"
                >
                  <span className="text-foreground-subtle">{label}</span>
                  <span className="max-w-[65%] text-right font-semibold">{value}</span>
                </div>
              ))}
            </div>
          </SectionCard>
        </div>
      </aside>
    </div>
  )
}

export function CalculatorList({
  calculators,
  onToggle,
  onEdit,
}: {
  calculators: PricingCalculator[]
  onToggle: (item: PricingCalculator) => void
  onEdit: (item: PricingCalculator) => void
}) {
  return (
    <div className="grid gap-2.5 xl:grid-cols-2">
      {calculators.map((calculator) => (
        <article key={calculator.id} className="border-border rounded-card border p-3">
          <div className="flex items-start justify-between gap-3">
            <div className="flex gap-2.5">
              <span className="bg-brand-50 text-brand-700 grid size-9 place-items-center rounded-xl">
                <IconCalculator size={18} />
              </span>
              <div>
                <h3 className="text-[0.6875rem] font-extrabold">{calculator.name}</h3>
                <p className="text-foreground-subtle mt-0.5 text-[0.5625rem]">
                  {calculator.code} · {calculator.serviceName} · v{calculator.version}
                </p>
              </div>
            </div>
            <StatusPill status={calculator.status} />
          </div>
          <p className="text-foreground-subtle mt-2 text-[0.625rem] leading-4">
            {calculator.description}
          </p>
          <div className="mt-2.5 grid grid-cols-3 gap-1.5">
            <MetricMini label="Variables" value={calculator.variables.length} />
            <MetricMini label="Charges" value={calculator.charges.length} />
            <MetricMini label="Sample" value={formatCurrency(calculator.sampleTotal)} />
          </div>
          <div className="mt-2.5 flex items-center justify-between">
            <span className="text-foreground-subtle text-[0.5625rem]">
              Updated {new Date(calculator.updatedAt).toLocaleDateString('en-NG')}
            </span>
            <div className="flex gap-1.5">
              <CompactActionButton onClick={() => onEdit(calculator)}>
                Configure
              </CompactActionButton>
              <CompactActionButton onClick={() => onToggle(calculator)}>
                {calculator.status === 'active' ? 'Deactivate' : 'Activate'}
              </CompactActionButton>
            </div>
          </div>
        </article>
      ))}
    </div>
  )
}

function MetricMini({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="bg-surface-muted rounded-lg p-1.5 text-center">
      <p className="text-[0.6875rem] font-extrabold">{value}</p>
      <p className="text-foreground-subtle text-[0.5rem] uppercase">{label}</p>
    </div>
  )
}

export function RequestFormCards({
  forms,
  onToggle,
  onEdit,
}: {
  forms: ServiceRequestForm[]
  onToggle: (item: ServiceRequestForm) => void
  onEdit: (item: ServiceRequestForm) => void
}) {
  return (
    <div className="grid gap-2.5 xl:grid-cols-2">
      {forms.map((form) => (
        <article key={form.id} className="border-border rounded-card border p-3">
          <div className="flex items-start justify-between gap-3">
            <div className="flex gap-2.5">
              <span className="bg-brand-50 text-brand-700 grid size-9 place-items-center rounded-xl">
                <IconClipboardText size={18} />
              </span>
              <div>
                <h3 className="text-[0.6875rem] font-extrabold">{form.name}</h3>
                <p className="text-foreground-subtle text-[0.5625rem]">
                  {form.serviceName} · Version {form.version}
                </p>
              </div>
            </div>
            <StatusPill status={form.status} />
          </div>
          <div className="mt-3 space-y-1.5">
            {form.fields.slice(0, 5).map((field, index) => (
              <div
                key={field.id}
                className="bg-surface-muted flex items-center justify-between rounded-lg px-2.5 py-1.5"
              >
                <div className="flex min-w-0 items-center gap-2">
                  <span className="text-foreground-subtle text-[0.5625rem] font-bold">
                    {index + 1}
                  </span>
                  <span className="truncate text-[0.625rem] font-semibold">{field.label}</span>
                </div>
                <span className="text-foreground-subtle text-[0.5rem] uppercase">
                  {field.type}
                  {field.required ? ' · required' : ''}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-2.5 flex items-center justify-between">
            <span className="text-foreground-subtle text-[0.5625rem]">
              {form.fields.length} fields
            </span>
            <div className="flex gap-1.5">
              <CompactActionButton onClick={() => onEdit(form)}>Open Builder</CompactActionButton>
              <CompactActionButton onClick={() => onToggle(form)}>
                {form.status === 'active' ? 'Create new version' : 'Activate'}
              </CompactActionButton>
            </div>
          </div>
        </article>
      ))}
    </div>
  )
}

export function WorkflowCards({
  workflows,
  onToggle,
  onEdit,
}: {
  workflows: ServiceWorkflow[]
  onToggle: (item: ServiceWorkflow) => void
  onEdit: (item: ServiceWorkflow) => void
}) {
  return (
    <div className="space-y-2.5">
      {workflows.map((workflow) => (
        <article key={workflow.id} className="border-border rounded-card border p-3">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <IconGitBranch size={16} className="text-brand-700" />
                <h3 className="text-[0.6875rem] font-extrabold">{workflow.name}</h3>
                <StatusPill status={workflow.status} />
              </div>
              <p className="text-foreground-subtle mt-0.5 text-[0.5625rem]">
                {workflow.serviceName} · Version {workflow.version}
              </p>
            </div>
            <div className="flex gap-1.5">
              <CompactActionButton onClick={() => onEdit(workflow)}>
                Open Designer
              </CompactActionButton>
              <CompactActionButton onClick={() => onToggle(workflow)}>
                {workflow.status === 'active' ? 'Create new version' : 'Activate workflow'}
              </CompactActionButton>
            </div>
          </div>
          <div className="mt-3 flex min-w-max items-stretch gap-1 overflow-x-auto pb-1">
            {workflow.stages
              .slice()
              .sort((a, b) => a.order - b.order)
              .map((stage, index) => (
                <div key={stage.id} className="flex items-center gap-1">
                  <div className="border-border bg-surface-muted w-40 rounded-lg border p-2">
                    <div className="flex items-center justify-between">
                      <span className="bg-brand-600 grid size-5 place-items-center rounded-full text-[0.5625rem] font-bold text-white">
                        {stage.order}
                      </span>
                      <span className="text-foreground-subtle text-[0.5rem]">
                        {stage.slaHours}h SLA
                      </span>
                    </div>
                    <p className="mt-1.5 truncate text-[0.625rem] font-bold">{stage.name}</p>
                    <p className="text-foreground-subtle mt-0.5 truncate text-[0.5rem]">
                      {stage.ownerRole}
                    </p>
                    <div className="mt-1.5 flex gap-1">
                      {stage.requiresEvidence ? <Flag label="Evidence" /> : null}
                      {stage.requiresApproval ? <Flag label="Approval" /> : null}
                      {stage.clientVisible ? <Flag label="Client" /> : null}
                    </div>
                  </div>
                  {index < workflow.stages.length - 1 ? (
                    <IconChevronRight size={14} className="text-foreground-subtle" />
                  ) : null}
                </div>
              ))}
          </div>
        </article>
      ))}
    </div>
  )
}

function Flag({ label }: { label: string }) {
  return (
    <span className="bg-brand-50 text-brand-700 rounded px-1 py-0.5 text-[0.4375rem] font-bold">
      {label}
    </span>
  )
}

export function BranchMatrix({
  activations,
  onToggle,
}: {
  activations: BranchActivation[]
  onToggle: (item: BranchActivation) => void
}) {
  const services = useMemo(
    () =>
      Array.from(new Map(activations.map((item) => [item.serviceId, item.serviceName])).entries()),
    [activations],
  )
  const branches = useMemo(
    () =>
      Array.from(new Map(activations.map((item) => [item.branchId, item.branchName])).entries()),
    [activations],
  )

  return (
    <div className="border-border rounded-card overflow-x-auto border">
      <table className="w-full min-w-[820px] border-collapse text-left">
        <thead className="bg-surface-muted">
          <tr className="text-foreground-subtle text-[0.5625rem] font-bold tracking-[0.08em] uppercase">
            <th className="px-3 py-2.5">Service</th>
            {branches.map(([id, name]) => (
              <th key={id} className="px-3 py-2.5">
                {name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-border divide-y">
          {services.map(([serviceId, serviceName]) => (
            <tr key={serviceId}>
              <td className="px-3 py-2.5 text-[0.6875rem] font-bold">{serviceName}</td>
              {branches.map(([branchId]) => {
                const item = activations.find(
                  (activation) =>
                    activation.serviceId === serviceId && activation.branchId === branchId,
                )
                return (
                  <td key={branchId} className="px-3 py-2.5">
                    {item ? (
                      <button type="button" onClick={() => onToggle(item)} className="text-left">
                        <StatusPill status={item.state} />
                        <p className="text-foreground-subtle mt-1 text-[0.5rem]">
                          {item.capacity}% capacity · {item.activeOrders} orders
                        </p>
                      </button>
                    ) : (
                      <span className="text-foreground-subtle text-[0.5625rem]">
                        Not configured
                      </span>
                    )}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function NewServiceDialog({
  open,
  onClose,
  onSubmit,
  pending,
}: {
  open: boolean
  onClose: () => void
  onSubmit: (value: {
    name: string
    code: string
    division: string
    description: string
    owner: string
  }) => void
  pending: boolean
}) {
  const [value, setValue] = useState({
    name: '',
    code: '',
    division: 'Engineering',
    description: '',
    owner: '',
  })

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/35 p-4"
      onMouseDown={onClose}
    >
      <form
        className="bg-surface rounded-card w-full max-w-lg shadow-2xl"
        onMouseDown={(event) => event.stopPropagation()}
        onSubmit={(event) => {
          event.preventDefault()
          onSubmit(value)
        }}
      >
        <header className="border-border flex items-start justify-between border-b p-4">
          <div>
            <p className="text-brand-700 text-[0.5625rem] font-bold tracking-[0.1em] uppercase">
              Service setup
            </p>
            <h2 className="mt-1 text-sm font-extrabold">Create Service</h2>
            <p className="text-foreground-subtle mt-0.5 text-[0.625rem]">
              Start a draft service, then connect pricing, form, workflow and branches.
            </p>
          </div>
          <CompactActionButton onClick={onClose} tone="ghost">
            Close
          </CompactActionButton>
        </header>
        <div className="grid gap-3 p-4 sm:grid-cols-2">
          <Field
            label="Service name"
            value={value.name}
            onChange={(name) => setValue((current) => ({ ...current, name }))}
          />
          <Field
            label="Service code"
            value={value.code}
            onChange={(code) => setValue((current) => ({ ...current, code }))}
          />
          <label className="space-y-1">
            <span className="text-[0.625rem] font-bold">Division</span>
            <select
              value={value.division}
              onChange={(event) =>
                setValue((current) => ({ ...current, division: event.target.value }))
              }
              className="border-border rounded-control h-9 w-full border px-3 text-xs"
            >
              {['Engineering', 'Survey', 'Real Estate', 'ICT', 'Facility Management'].map(
                (division) => (
                  <option key={division}>{division}</option>
                ),
              )}
            </select>
          </label>
          <Field
            label="Service owner"
            value={value.owner}
            onChange={(owner) => setValue((current) => ({ ...current, owner }))}
          />
          <label className="space-y-1 sm:col-span-2">
            <span className="text-[0.625rem] font-bold">Description</span>
            <textarea
              value={value.description}
              onChange={(event) =>
                setValue((current) => ({ ...current, description: event.target.value }))
              }
              rows={4}
              className="border-border rounded-control w-full border p-3 text-xs"
            />
          </label>
        </div>
        <footer className="border-border flex justify-end gap-2 border-t p-3">
          <CompactActionButton onClick={onClose}>Cancel</CompactActionButton>
          <CompactActionButton type="submit" tone="primary" disabled={pending}>
            <IconPlus size={14} />
            {pending ? 'Creating…' : 'Create draft service'}
          </CompactActionButton>
        </footer>
      </form>
    </div>
  )
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (value: string) => void
}) {
  return (
    <label className="space-y-1">
      <span className="text-[0.625rem] font-bold">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="border-border rounded-control h-9 w-full border px-3 text-xs"
      />
    </label>
  )
}
