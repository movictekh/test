import { IconX } from '@tabler/icons-react'
import { useState, type FormEvent } from 'react'
import type { CreateServiceRequestInput, ServiceRequestPriority } from '../types/commercial.types'

const services = [
  ['Building Construction', 'Engineering & Construction'],
  ['Estate Plot Sales', 'Real Estate'],
  ['Structural Inspection', 'Engineering & Construction'],
  ['Cadastral Land Survey', 'Land Surveying & Geospatial'],
  ['Business Software Development', 'Information Technology'],
] as const

export function CreateRequestWorkspace({
  open,
  saving,
  onClose,
  onSubmit,
}: {
  open: boolean
  saving: boolean
  onClose: () => void
  onSubmit: (input: CreateServiceRequestInput) => void
}) {
  const [client, setClient] = useState('')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [service, setService] = useState<string>(services[0][0])
  const [branch, setBranch] = useState('Enugu')
  const [priority, setPriority] = useState<ServiceRequestPriority>('Medium')
  const [budget, setBudget] = useState('')
  const [dueAt, setDueAt] = useState('')
  const [details, setDetails] = useState('')
  const [location, setLocation] = useState('')
  if (!open) return null
  const save = (event: FormEvent, submit: boolean) => {
    event.preventDefault()
    const division = services.find(([name]) => name === service)?.[1] ?? ''
    onSubmit({
      client,
      clientType: 'Individual',
      phone,
      email,
      service,
      division,
      branch,
      source: 'Walk-in',
      priority,
      budget: Number(budget || 0),
      dueAt,
      details,
      intakeResponses: { Location: location },
      submit,
    })
  }
  return (
    <div className="commercial-modal-backdrop" onMouseDown={onClose}>
      <form
        className="commercial-modal"
        aria-label="Create service request"
        onSubmit={(e) => save(e, true)}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Create Service Request</h2>
            <p>Capture client demand and service intake details</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close">
            <IconX size={17} />
          </button>
        </header>
        <div className="commercial-modal-body">
          <div className="commercial-form-grid">
            <label>
              Client name *
              <input required value={client} onChange={(e) => setClient(e.target.value)} />
            </label>
            <label>
              Phone *<input required value={phone} onChange={(e) => setPhone(e.target.value)} />
            </label>
            <label>
              Email
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </label>
            <label>
              Service *
              <select value={service} onChange={(e) => setService(e.target.value)}>
                {services.map(([name]) => (
                  <option key={name}>{name}</option>
                ))}
              </select>
            </label>
            <label>
              Branch *
              <select value={branch} onChange={(e) => setBranch(e.target.value)}>
                {['Enugu', 'Port Harcourt', 'Lagos', 'Abuja'].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </label>
            <label>
              Priority
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as ServiceRequestPriority)}
              >
                {['Low', 'Medium', 'High', 'Urgent'].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </label>
            <label>
              Budget
              <input
                type="number"
                min="0"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
              />
            </label>
            <label>
              Required date *
              <input
                type="date"
                required
                value={dueAt}
                onChange={(e) => setDueAt(e.target.value)}
              />
            </label>
            <label className="commercial-form-span">
              Location
              <input value={location} onChange={(e) => setLocation(e.target.value)} />
            </label>
            <label className="commercial-form-span">
              Request description *
              <textarea
                required
                rows={4}
                value={details}
                onChange={(e) => setDetails(e.target.value)}
              />
            </label>
          </div>
        </div>
        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="commercial-btn"
            disabled={saving}
            onClick={(e) => {
              if (e.currentTarget.form?.reportValidity()) save(e, false)
            }}
          >
            Save Draft
          </button>
          <button type="submit" className="commercial-btn commercial-btn-primary" disabled={saving}>
            {saving ? 'Submitting...' : 'Submit Request'}
          </button>
        </footer>
      </form>
    </div>
  )
}
