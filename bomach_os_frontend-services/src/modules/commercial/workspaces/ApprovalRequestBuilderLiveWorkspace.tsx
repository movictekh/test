import { IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useState } from 'react'

import type { ApprovalFlow, CreateApprovalRequestInput } from '../approvals/approval.types'
import { validateApprovalRequest } from '../approvals/approval.validation'

export function ApprovalRequestBuilderLiveWorkspace({
  flows,
  saving,
  onClose,
  onSubmit,
}: {
  flows: ApprovalFlow[]
  saving: boolean
  onClose: () => void
  onSubmit: (input: CreateApprovalRequestInput) => void
}) {
  const [errors, setErrors] = useState<Record<string, string>>({})

  const form = useForm({
    defaultValues: {
      flowId: flows[0]?.id ?? 0,
      title: '',
      description: '',
    },
    onSubmit: ({ value }) => {
      const nextErrors = validateApprovalRequest(value)
      setErrors(nextErrors)
      if (Object.keys(nextErrors).length > 0) return

      onSubmit({
        flowId: Number(value.flowId),
        title: value.title.trim(),
        description: value.description.trim(),
      })
    },
  })

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <form
        className="commercial-modal commercial-modal--xl"
        aria-label="Create Approval Request"
        onMouseDown={(event) => event.stopPropagation()}
        onSubmit={(event) => {
          event.preventDefault()
          event.stopPropagation()
          void form.handleSubmit()
        }}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>New Approval Request</h2>
            <p>Route a request through an active approval flow</p>
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
            <h3>Approval flow</h3>
            <form.Field name="flowId">
              {(field) => (
                <label className="commercial-field commercial-field--full">
                  <span>Flow *</span>
                  <select
                    value={field.state.value}
                    onChange={(event) => {
                      if (errors.flowId) {
                        setErrors((current) => ({ ...current, flowId: '' }))
                      }
                      field.handleChange(Number(event.target.value))
                    }}
                  >
                    {flows.map((flow) => (
                      <option key={flow.id} value={flow.id}>
                        {flow.name} — {flow.actionTypeDisplay}
                      </option>
                    ))}
                  </select>
                  {errors.flowId ? (
                    <small className="commercial-field-error">{errors.flowId}</small>
                  ) : null}
                </label>
              )}
            </form.Field>

            <form.Subscribe selector={(state) => state.values.flowId}>
              {(flowId) => {
                const selected = flows.find((flow) => flow.id === Number(flowId))
                if (!selected) return null
                return (
                  <div className="commercial-info-grid">
                    <div>
                      <div className="commercial-kl">Type</div>
                      <b>{selected.actionTypeDisplay}</b>
                    </div>
                    <div>
                      <div className="commercial-kl">Steps</div>
                      <b>{selected.steps.length}</b>
                    </div>
                    <div className="commercial-info-full">
                      <div className="commercial-kl">Description</div>
                      <p>{selected.description || '—'}</p>
                    </div>
                  </div>
                )
              }}
            </form.Subscribe>
          </section>

          <section className="commercial-form-section">
            <h3>Request</h3>
            <div className="commercial-form-grid">
              <form.Field name="title">
                {(field) => (
                  <label className="commercial-field commercial-field--full">
                    <span>Title *</span>
                    <input
                      value={field.state.value}
                      onChange={(event) => {
                        if (errors.title) {
                          setErrors((current) => ({ ...current, title: '' }))
                        }
                        field.handleChange(event.target.value)
                      }}
                      placeholder="Short description of what needs approval"
                    />
                    {errors.title ? (
                      <small className="commercial-field-error">{errors.title}</small>
                    ) : null}
                  </label>
                )}
              </form.Field>

              <form.Field name="description">
                {(field) => (
                  <label className="commercial-field commercial-field--full">
                    <span>Description *</span>
                    <textarea
                      rows={5}
                      value={field.state.value}
                      onChange={(event) => {
                        if (errors.description) {
                          setErrors((current) => ({
                            ...current,
                            description: '',
                          }))
                        }
                        field.handleChange(event.target.value)
                      }}
                      placeholder="Give the approvers the context needed to make a decision"
                    />
                    {errors.description ? (
                      <small className="commercial-field-error">{errors.description}</small>
                    ) : null}
                  </label>
                )}
              </form.Field>
            </div>
          </section>
        </div>

        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" disabled={saving} onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className="commercial-btn commercial-btn-primary"
            disabled={saving || flows.length === 0}
          >
            {saving ? 'Creating...' : 'Create Approval Request'}
          </button>
        </footer>
      </form>
    </div>
  )
}
