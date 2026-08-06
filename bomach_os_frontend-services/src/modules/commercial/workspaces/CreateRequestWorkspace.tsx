import { IconCalculator, IconX } from '@tabler/icons-react'
import { useForm, type ReactFormExtendedApi } from '@tanstack/react-form'
import { useMemo, useState } from 'react'

import { useToast } from '@/shared/ui'
import type {
  RequestFormField,
  ServiceAdministrationWorkspace,
} from '@/modules/service-administration/types/service-administration.types'

import type { CreateServiceRequestInput, ServiceRequestPriority } from '../types/commercial.types'
import {
  buildInitialDynamicValues,
  getActiveBranches,
  getActiveCalculator,
  getActiveRequestForm,
  getActiveServices,
} from './create-request-workspace.rules'

interface CreateRequestFormValues {
  client: string
  clientType: string
  phone: string
  email: string
  serviceId: string
  branch: string
  source: string
  priority: ServiceRequestPriority
  budget: number
  dueAt: string
  details: string
  consent: boolean
  intakeResponses: Record<string, string>
  calculatorInputs: Record<string, string>
}

type CreateRequestFormApi = ReactFormExtendedApi<
  CreateRequestFormValues,
  undefined,
  undefined,
  undefined,
  undefined,
  undefined,
  undefined,
  undefined,
  undefined,
  undefined,
  undefined,
  unknown
>

const customerTypes = [
  'Individual',
  'Company',
  'Family / Group',
  'Cooperative',
  'Government',
  'Partner / Realtor',
] as const

const sources = [
  'Client Portal',
  'Sales / CRM',
  'Walk-in',
  'Meta Ads',
  'WhatsApp',
  'Referral',
  'External Realtor',
  'Partner',
] as const

const priorities: Array<{
  label: string
  value: ServiceRequestPriority
}> = [
  { label: 'Normal', value: 'Medium' },
  { label: 'High', value: 'High' },
  { label: 'Critical', value: 'Urgent' },
]

const money = new Intl.NumberFormat('en-NG', {
  style: 'currency',
  currency: 'NGN',
  maximumFractionDigits: 0,
})

function DynamicRequestField({
  field,
  form,
}: {
  field: RequestFormField
  form: CreateRequestFormApi
}) {
  return (
    <form.Subscribe selector={(state) => state.values.intakeResponses[field.key] ?? ''}>
      {(value) => {
        const setValue = (next: string) => {
          form.setFieldValue('intakeResponses', {
            ...form.state.values.intakeResponses,
            [field.key]: next,
          })
        }

        const label = (
          <span>
            {field.label}
            {field.required ? ' *' : ''}
          </span>
        )

        if (field.type === 'textarea') {
          return (
            <label className="commercial-field commercial-field--full">
              {label}
              <textarea rows={4} value={value} onChange={(event) => setValue(event.target.value)} />
              {field.helpText ? <small>{field.helpText}</small> : null}
            </label>
          )
        }

        if (field.type === 'select') {
          return (
            <label className="commercial-field">
              {label}
              <select value={value} onChange={(event) => setValue(event.target.value)}>
                <option value="">Select</option>
                {(field.options ?? []).map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              {field.helpText ? <small>{field.helpText}</small> : null}
            </label>
          )
        }

        if (field.type === 'checkbox') {
          return (
            <label className="commercial-check commercial-field--full">
              <input
                type="checkbox"
                checked={value === 'true'}
                onChange={(event) => setValue(String(event.target.checked))}
              />
              {field.label}
              {field.required ? ' *' : ''}
            </label>
          )
        }

        if (field.type === 'file') {
          return (
            <label className="commercial-field">
              {label}
              <input
                type="file"
                onChange={(event) =>
                  setValue(
                    Array.from(event.target.files ?? [])
                      .map((file) => file.name)
                      .join(', '),
                  )
                }
              />
              {field.helpText ? <small>{field.helpText}</small> : null}
            </label>
          )
        }

        return (
          <label className="commercial-field">
            {label}
            <input
              type={field.type === 'number' ? 'number' : field.type === 'date' ? 'date' : 'text'}
              value={value}
              onChange={(event) => setValue(event.target.value)}
            />
            {field.helpText ? <small>{field.helpText}</small> : null}
          </label>
        )
      }}
    </form.Subscribe>
  )
}

export function CreateRequestWorkspace({
  saving,
  serviceWorkspace,
  onClose,
  onSubmit,
}: {
  saving: boolean
  serviceWorkspace: ServiceAdministrationWorkspace
  onClose: () => void
  onSubmit: (input: CreateServiceRequestInput) => void
}) {
  const toast = useToast()
  const activeServices = useMemo(() => getActiveServices(serviceWorkspace), [serviceWorkspace])
  const initialServiceId = activeServices[0]?.id ?? ''
  const initialBranches = getActiveBranches(serviceWorkspace, initialServiceId)
  const initialFields = getActiveRequestForm(serviceWorkspace, initialServiceId)?.fields ?? []

  const [selectedServiceId, setSelectedServiceId] = useState(initialServiceId)
  const [estimate, setEstimate] = useState<number | null>(null)

  const selectedService = activeServices.find((service) => service.id === selectedServiceId) ?? null

  const activeBranches = useMemo(
    () => getActiveBranches(serviceWorkspace, selectedServiceId),
    [selectedServiceId, serviceWorkspace],
  )
  const requestForm = useMemo(
    () => getActiveRequestForm(serviceWorkspace, selectedServiceId),
    [selectedServiceId, serviceWorkspace],
  )
  const calculator = useMemo(
    () => getActiveCalculator(serviceWorkspace, selectedServiceId),
    [selectedServiceId, serviceWorkspace],
  )

  const defaultValues: CreateRequestFormValues = {
    client: '',
    clientType: customerTypes[0],
    phone: '',
    email: '',
    serviceId: initialServiceId,
    branch: initialBranches[0] ?? '',
    source: sources[0],
    priority: 'Medium',
    budget: 0,
    dueAt: '',
    details: '',
    consent: true,
    intakeResponses: buildInitialDynamicValues(initialFields),
    calculatorInputs: {},
  }

  const form = useForm({
    defaultValues,
    onSubmit: ({ value }) => {
      if (!selectedService) {
        toast.error('Select an active service')
        return
      }

      if (!activeBranches.includes(value.branch)) {
        toast.error('Select an active branch', {
          description: 'This service is not active in the selected branch.',
        })
        return
      }

      if (!value.consent) {
        toast.error('Client consent is required')
        return
      }

      onSubmit({
        client: value.client.trim(),
        clientType: value.clientType,
        phone: value.phone.trim(),
        email: value.email.trim(),
        service: selectedService.name,
        division: selectedService.division,
        branch: value.branch,
        source: value.source,
        priority: value.priority,
        budget: Number(value.budget || estimate || 0),
        dueAt: value.dueAt,
        details: value.details.trim(),
        intakeResponses: {
          ...value.intakeResponses,
          ...Object.fromEntries(
            Object.entries(value.calculatorInputs).map(([key, item]) => [
              `Calculator: ${key}`,
              item,
            ]),
          ),
          ...(calculator
            ? {
                'Calculator used': calculator.name,
                'Calculator version': String(calculator.version),
                'Calculated estimate': String(estimate ?? calculator.sampleTotal),
              }
            : {}),
          Consent: 'Recorded',
        },
        submit: true,
      })
    },
  })

  const chooseService = (serviceId: string) => {
    const branches = getActiveBranches(serviceWorkspace, serviceId)
    const fields = getActiveRequestForm(serviceWorkspace, serviceId)?.fields ?? []

    setSelectedServiceId(serviceId)
    setEstimate(null)
    form.setFieldValue('serviceId', serviceId)
    form.setFieldValue('branch', branches[0] ?? '')
    form.setFieldValue('budget', 0)
    form.setFieldValue('intakeResponses', buildInitialDynamicValues(fields))
    form.setFieldValue('calculatorInputs', {})
  }

  const calculateEstimate = () => {
    if (!calculator) {
      toast.error('No active calculator assigned', {
        description: 'This service has no active pricing calculator.',
      })
      return
    }

    setEstimate(calculator.sampleTotal)
    form.setFieldValue('budget', calculator.sampleTotal)
    toast.success(`Estimate calculated: ${money.format(calculator.sampleTotal)}`)
  }

  if (activeServices.length === 0) {
    return (
      <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
        <section
          className="commercial-modal"
          role="dialog"
          aria-modal="true"
          aria-label="Create Service Request"
          onMouseDown={(event) => event.stopPropagation()}
        >
          <header className="commercial-modal-header">
            <h2>Create Service Request</h2>
            <button type="button" className="commercial-modal-close" onClick={onClose}>
              <IconX size={16} />
            </button>
          </header>
          <div className="commercial-empty">
            No active services are available. Activate a service in Service Catalogue first.
          </div>
        </section>
      </div>
    )
  }

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <form
        className="commercial-modal commercial-modal--xl"
        aria-label="Create Service Request"
        onSubmit={(event) => {
          event.preventDefault()
          event.stopPropagation()
          void form.handleSubmit()
        }}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Create Service Request</h2>
            <p>Service-driven commercial intake</p>
          </div>
          <button
            type="button"
            className="commercial-modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            <IconX size={16} />
          </button>
        </header>

        <div className="commercial-modal-body">
          <section className="commercial-form-section">
            <h3>Client information</h3>
            <div className="commercial-form-grid">
              <form.Field
                name="client"
                validators={{
                  onBlur: ({ value }) => (value.trim() ? undefined : 'Client name is required'),
                }}
              >
                {(field) => (
                  <label className="commercial-field">
                    <span>Client / organization *</span>
                    <input
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(event) => field.handleChange(event.target.value)}
                    />
                    {field.state.meta.errors[0] ? (
                      <em>{String(field.state.meta.errors[0])}</em>
                    ) : null}
                  </label>
                )}
              </form.Field>

              <form.Field name="clientType">
                {(field) => (
                  <label className="commercial-field">
                    <span>Customer type</span>
                    <select
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                    >
                      {customerTypes.map((type) => (
                        <option key={type}>{type}</option>
                      ))}
                    </select>
                  </label>
                )}
              </form.Field>

              <form.Field
                name="phone"
                validators={{
                  onBlur: ({ value }) => (value.trim() ? undefined : 'Phone is required'),
                }}
              >
                {(field) => (
                  <label className="commercial-field">
                    <span>Phone *</span>
                    <input
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(event) => field.handleChange(event.target.value)}
                    />
                    {field.state.meta.errors[0] ? (
                      <em>{String(field.state.meta.errors[0])}</em>
                    ) : null}
                  </label>
                )}
              </form.Field>

              <form.Field name="email">
                {(field) => (
                  <label className="commercial-field">
                    <span>Email</span>
                    <input
                      type="email"
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                    />
                  </label>
                )}
              </form.Field>
            </div>
          </section>

          <section className="commercial-form-section">
            <h3>Service and branch</h3>
            <div className="commercial-form-grid">
              <label className="commercial-field">
                <span>Division</span>
                <input value={selectedService?.division ?? ''} readOnly />
              </label>

              <form.Field name="serviceId">
                {(field) => (
                  <label className="commercial-field">
                    <span>Active service *</span>
                    <select
                      value={field.state.value}
                      onChange={(event) => {
                        field.handleChange(event.target.value)
                        chooseService(event.target.value)
                      }}
                    >
                      {activeServices.map((service) => (
                        <option key={service.id} value={service.id}>
                          {service.name}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </form.Field>

              <form.Field
                name="branch"
                validators={{
                  onBlur: ({ value }) => (value ? undefined : 'An active branch is required'),
                }}
              >
                {(field) => (
                  <label className="commercial-field">
                    <span>Active branch *</span>
                    <select
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(event) => field.handleChange(event.target.value)}
                    >
                      {activeBranches.length === 0 ? (
                        <option value="">No active branches</option>
                      ) : (
                        activeBranches.map((branch) => <option key={branch}>{branch}</option>)
                      )}
                    </select>
                    {field.state.meta.errors[0] ? (
                      <em>{String(field.state.meta.errors[0])}</em>
                    ) : null}
                  </label>
                )}
              </form.Field>

              <form.Field name="source">
                {(field) => (
                  <label className="commercial-field">
                    <span>Source</span>
                    <select
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                    >
                      {sources.map((source) => (
                        <option key={source}>{source}</option>
                      ))}
                    </select>
                  </label>
                )}
              </form.Field>
            </div>
          </section>

          {requestForm ? (
            <section className="commercial-form-section">
              <h3>{requestForm.name}</h3>
              <p className="commercial-form-note">
                Version {requestForm.version} · configured in Request Form Builder
              </p>
              <div className="commercial-form-grid">
                {requestForm.fields.map((field) => (
                  <DynamicRequestField
                    key={field.id}
                    field={field}
                    form={form as CreateRequestFormApi}
                  />
                ))}
              </div>
            </section>
          ) : (
            <section className="commercial-form-section commercial-config-warning">
              No active request form is configured for this service.
            </section>
          )}

          <section className="commercial-form-section">
            <div className="commercial-form-section-heading">
              <div>
                <h3>Pricing estimate</h3>
                <p>
                  {calculator
                    ? `${calculator.name} · version ${calculator.version}`
                    : 'No active calculator assigned'}
                </p>
              </div>
              <button
                type="button"
                className="commercial-btn"
                onClick={calculateEstimate}
                disabled={!calculator}
              >
                <IconCalculator size={14} />
                Calculate Estimate
              </button>
            </div>

            {calculator ? (
              <div className="commercial-form-grid">
                {calculator.variables.map((variable) => {
                  const name = `calculatorInputs.${variable.key}` as never
                  return (
                    <form.Field key={variable.id} name={name}>
                      {(field) => (
                        <label className="commercial-field">
                          <span>
                            {variable.label}
                            {variable.unit ? ` (${variable.unit})` : ''}
                          </span>
                          {variable.type === 'select' ? (
                            <input
                              value={String(field.state.value ?? '')}
                              onChange={(event) => field.handleChange(event.target.value as never)}
                            />
                          ) : variable.type === 'boolean' ? (
                            <select
                              value={String(field.state.value ?? '')}
                              onChange={(event) => field.handleChange(event.target.value as never)}
                            >
                              <option value="">Select</option>
                              <option value="true">Yes</option>
                              <option value="false">No</option>
                            </select>
                          ) : (
                            <input
                              type="number"
                              value={String(field.state.value ?? '')}
                              onChange={(event) => field.handleChange(event.target.value as never)}
                            />
                          )}
                        </label>
                      )}
                    </form.Field>
                  )
                })}

                <form.Field name="budget">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Commercial budget / estimate</span>
                      <input
                        type="number"
                        min={0}
                        value={field.state.value}
                        onChange={(event) => field.handleChange(Number(event.target.value || 0))}
                      />
                      {estimate != null ? <small>{money.format(estimate)}</small> : null}
                    </label>
                  )}
                </form.Field>
              </div>
            ) : null}
          </section>

          <section className="commercial-form-section">
            <h3>Request control</h3>
            <div className="commercial-form-grid">
              <form.Field name="priority">
                {(field) => (
                  <label className="commercial-field">
                    <span>Priority</span>
                    <select
                      value={field.state.value}
                      onChange={(event) =>
                        field.handleChange(event.target.value as ServiceRequestPriority)
                      }
                    >
                      {priorities.map((priority) => (
                        <option key={priority.value} value={priority.value}>
                          {priority.label}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </form.Field>

              <form.Field
                name="dueAt"
                validators={{
                  onBlur: ({ value }) => (value ? undefined : 'Preferred date is required'),
                }}
              >
                {(field) => (
                  <label className="commercial-field">
                    <span>Preferred date *</span>
                    <input
                      type="date"
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(event) => field.handleChange(event.target.value)}
                    />
                    {field.state.meta.errors[0] ? (
                      <em>{String(field.state.meta.errors[0])}</em>
                    ) : null}
                  </label>
                )}
              </form.Field>

              <form.Field
                name="details"
                validators={{
                  onBlur: ({ value }) => (value.trim() ? undefined : 'Scope is required'),
                }}
              >
                {(field) => (
                  <label className="commercial-field commercial-field--full">
                    <span>Scope / details *</span>
                    <textarea
                      rows={4}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(event) => field.handleChange(event.target.value)}
                    />
                    {field.state.meta.errors[0] ? (
                      <em>{String(field.state.meta.errors[0])}</em>
                    ) : null}
                  </label>
                )}
              </form.Field>

              <form.Field name="consent">
                {(field) => (
                  <label className="commercial-check commercial-field--full">
                    <input
                      type="checkbox"
                      checked={field.state.value}
                      onChange={(event) => field.handleChange(event.target.checked)}
                    />
                    Client consent and privacy notice recorded
                  </label>
                )}
              </form.Field>
            </div>
          </section>
        </div>

        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <form.Subscribe selector={(state) => [state.canSubmit, state.isSubmitting]}>
            {([canSubmit, isSubmitting]) => (
              <button
                type="submit"
                className="commercial-btn commercial-btn-primary"
                disabled={!canSubmit || saving || isSubmitting || activeBranches.length === 0}
              >
                {saving || isSubmitting ? 'Submitting...' : 'Submit Request'}
              </button>
            )}
          </form.Subscribe>
        </footer>
      </form>
    </div>
  )
}
