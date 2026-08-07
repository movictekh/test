import { IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useState } from 'react'

import { formatNumberFieldValue, parseNumberFieldValue } from '@/shared/lib/number-input'

import type { CreateServiceOrderInput } from '../types/fulfillment.types'

type ServiceOption = {
  name: string
  division: string
  workflowStages: string[]
}

type Draft = Pick<
  CreateServiceOrderInput,
  'client' | 'service' | 'value' | 'dueAt' | 'owner' | 'mode'
>

export function CreateOrderWorkspace({
  services,
  saving,
  onClose,
  onSubmit,
}: {
  services: ServiceOption[]
  saving: boolean
  onClose: () => void
  onSubmit: (draft: Draft) => void
}) {
  const [error, setError] = useState('')
  const form = useForm({
    defaultValues: {
      client: '',
      service: services[0]?.name ?? '',
      value: 0,
      dueAt: '2026-07-30',
      owner: 'Service Manager',
      mode: 'Quick service order',
    } satisfies Draft,
  })

  const submit = () => {
    const value = form.state.values
    if (
      !value.client.trim() ||
      !value.service ||
      !value.owner.trim() ||
      !value.dueAt ||
      value.value <= 0
    ) {
      setError('Complete all required order fields.')
      return
    }
    setError('')
    onSubmit(value)
  }

  return (
    <div className="fulfillment-modal-backdrop" onMouseDown={onClose}>
      <form
        className="fulfillment-modal"
        aria-label="Create Service Order"
        onMouseDown={(event) => event.stopPropagation()}
        onSubmit={(event) => {
          event.preventDefault()
          submit()
        }}
      >
        <header className="fulfillment-modal-header">
          <h2>Create Service Order</h2>
          <button
            type="button"
            className="fulfillment-modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            <IconX size={16} />
          </button>
        </header>

        <div className="fulfillment-modal-body">
          {error ? <div className="fulfillment-notice fulfillment-notice-red">{error}</div> : null}
          <div className="fulfillment-form-grid">
            <form.Field name="client">
              {(field) => (
                <label className="fulfillment-field">
                  <span>Client</span>
                  <input
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                  />
                </label>
              )}
            </form.Field>

            <form.Field name="service">
              {(field) => (
                <label className="fulfillment-field">
                  <span>Service</span>
                  <select
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                  >
                    {services.map((service) => (
                      <option key={service.name}>{service.name}</option>
                    ))}
                  </select>
                </label>
              )}
            </form.Field>

            <form.Field name="value">
              {(field) => (
                <label className="fulfillment-field">
                  <span>Order value</span>
                  <input
                    type="number"
                    min="1"
                    value={formatNumberFieldValue(field.state.value)}
                    onChange={(event) =>
                      field.handleChange(parseNumberFieldValue(event.target.value))
                    }
                  />
                </label>
              )}
            </form.Field>

            <form.Field name="dueAt">
              {(field) => (
                <label className="fulfillment-field">
                  <span>Due date</span>
                  <input
                    type="date"
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                  />
                </label>
              )}
            </form.Field>

            <form.Field name="owner">
              {(field) => (
                <label className="fulfillment-field">
                  <span>Owner</span>
                  <input
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                  />
                </label>
              )}
            </form.Field>

            <form.Field name="mode">
              {(field) => (
                <label className="fulfillment-field">
                  <span>Fulfillment mode</span>
                  <select
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                  >
                    <option>Quick service order</option>
                    <option>Managed service case</option>
                    <option>Project & worksite</option>
                  </select>
                </label>
              )}
            </form.Field>
          </div>
        </div>

        <footer className="fulfillment-modal-footer">
          <button type="button" className="fulfillment-btn" onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className="fulfillment-btn fulfillment-btn-primary"
            disabled={saving}
          >
            {saving ? 'Creating...' : 'Create Order'}
          </button>
        </footer>
      </form>
    </div>
  )
}
