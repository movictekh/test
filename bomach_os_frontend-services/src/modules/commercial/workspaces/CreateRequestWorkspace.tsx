import { IconX } from '@tabler/icons-react'
import { useMemo, useState, type FormEvent } from 'react'

import { useToast } from '@/shared/ui'

import type { CreateServiceRequestInput, ServiceRequestPriority } from '../types/commercial.types'

const divisions = [
  'Real Estate',
  'Land Surveying & Geospatial',
  'Engineering & Construction',
  'Courier & Logistics',
  'Information Technology',
  'Food & Farms',
  'Hospitality Services',
] as const

const catalogue: ReadonlyArray<{ name: string; division: string; estimate: number }> = [
  { name: 'Estate Plot Sales', division: 'Real Estate', estimate: 5_000_000 },
  { name: 'Property Brokerage', division: 'Real Estate', estimate: 2_500_000 },
  { name: 'Cadastral Land Survey', division: 'Land Surveying & Geospatial', estimate: 450_000 },
  { name: 'Building Construction', division: 'Engineering & Construction', estimate: 165_000_000 },
  { name: 'Structural Inspection', division: 'Engineering & Construction', estimate: 350_000 },
  { name: 'Express Delivery', division: 'Courier & Logistics', estimate: 25_000 },
  {
    name: 'Business Software Development',
    division: 'Information Technology',
    estimate: 8_500_000,
  },
  { name: 'Farm Produce Supply', division: 'Food & Farms', estimate: 1_200_000 },
]

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

const branches = ['Enugu', 'Port Harcourt', 'Lagos', 'Abuja'] as const

const priorityOptions = [
  { label: 'Normal', value: 'Medium' as const },
  { label: 'High', value: 'High' as const },
  { label: 'Critical', value: 'Urgent' as const },
]

const money = new Intl.NumberFormat('en-NG', {
  style: 'currency',
  currency: 'NGN',
  maximumFractionDigits: 0,
})

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
  const toast = useToast()
  const [client, setClient] = useState('')
  const [clientType, setClientType] = useState<string>(customerTypes[0])
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [division, setDivision] = useState<string>(divisions[0])
  const [service, setService] = useState('')
  const [branch, setBranch] = useState<string>(branches[0])
  const [source, setSource] = useState<string>(sources[0])
  const [budget, setBudget] = useState('0')
  const [priority, setPriority] = useState<ServiceRequestPriority>('Medium')
  const [details, setDetails] = useState('')
  const [dueAt, setDueAt] = useState('2026-07-20')
  const [lead, setLead] = useState('')
  const [consent, setConsent] = useState(true)
  const [estimate, setEstimate] = useState<number | null>(null)

  const servicesForDivision = useMemo(
    () => catalogue.filter((item) => item.division === division),
    [division],
  )

  const selectedService =
    servicesForDivision.find((item) => item.name === service) ?? servicesForDivision[0]

  if (!open) return null

  const activeServiceName = selectedService?.name ?? ''

  const changeDivision = (next: string) => {
    setDivision(next)
    const first = catalogue.find((item) => item.division === next)
    setService(first?.name ?? '')
    setEstimate(null)
  }

  const calculateEstimate = () => {
    if (!selectedService) {
      toast.error('No calculator assigned', {
        description: 'Select a service with a pricing calculator first.',
      })
      return
    }
    setEstimate(selectedService.estimate)
    setBudget(String(selectedService.estimate))
    toast.success(`Default estimate: ${money.format(selectedService.estimate)}`)
  }

  const save = (event: FormEvent) => {
    event.preventDefault()
    if (!consent) {
      toast.error('Client consent is required')
      return
    }
    if (!activeServiceName) {
      toast.error('Select a service')
      return
    }

    onSubmit({
      client: client.trim(),
      clientType,
      phone: phone.trim(),
      email: email.trim(),
      service: activeServiceName,
      division,
      branch,
      source,
      priority,
      budget: Number(budget || 0),
      dueAt,
      details: details.trim(),
      intakeResponses: {
        ...(lead.trim() ? { 'Lead / campaign reference': lead.trim() } : {}),
        ...(estimate != null ? { Estimate: String(estimate) } : {}),
        Consent: consent ? 'Recorded' : 'Missing',
      },
      submit: true,
    })
  }

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <form
        className="commercial-modal commercial-modal--xl"
        aria-label="Create Service Request"
        onSubmit={save}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="commercial-modal-header">
          <h2>Create Service Request</h2>
          <button type="button" className="commercial-modal-close" onClick={onClose} aria-label="Close">
            <IconX size={16} />
          </button>
        </header>

        <div className="commercial-modal-body">
          <div className="commercial-form-grid">
            <label className="commercial-field">
              <span>Client / organization</span>
              <input required value={client} onChange={(event) => setClient(event.target.value)} />
            </label>

            <label className="commercial-field">
              <span>Customer type</span>
              <select value={clientType} onChange={(event) => setClientType(event.target.value)}>
                {customerTypes.map((type) => (
                  <option key={type}>{type}</option>
                ))}
              </select>
            </label>

            <label className="commercial-field">
              <span>Phone</span>
              <input required value={phone} onChange={(event) => setPhone(event.target.value)} />
            </label>

            <label className="commercial-field">
              <span>Email</span>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>

            <label className="commercial-field">
              <span>Division</span>
              <select value={division} onChange={(event) => changeDivision(event.target.value)}>
                {divisions.map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </label>

            <label className="commercial-field">
              <span>Service</span>
              <select
                required
                value={activeServiceName}
                onChange={(event) => {
                  setService(event.target.value)
                  setEstimate(null)
                }}
              >
                {servicesForDivision.length === 0 ? (
                  <option value="">No services in division</option>
                ) : (
                  servicesForDivision.map((item) => (
                    <option key={item.name}>{item.name}</option>
                  ))
                )}
              </select>
            </label>

            <label className="commercial-field">
              <span>Branch</span>
              <select value={branch} onChange={(event) => setBranch(event.target.value)}>
                {branches.map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </label>

            <label className="commercial-field">
              <span>Source</span>
              <select value={source} onChange={(event) => setSource(event.target.value)}>
                {sources.map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </label>

            <label className="commercial-field">
              <span>Budget</span>
              <input
                type="number"
                min={0}
                value={budget}
                onChange={(event) => setBudget(event.target.value)}
              />
            </label>

            <label className="commercial-field">
              <span>Priority</span>
              <select
                value={priority}
                onChange={(event) => setPriority(event.target.value as ServiceRequestPriority)}
              >
                {priorityOptions.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="commercial-field commercial-field--full">
              <span>Scope / details</span>
              <textarea
                required
                rows={4}
                value={details}
                onChange={(event) => setDetails(event.target.value)}
              />
            </label>

            <label className="commercial-field">
              <span>Preferred date</span>
              <input
                type="date"
                required
                value={dueAt}
                onChange={(event) => setDueAt(event.target.value)}
              />
            </label>

            <label className="commercial-field">
              <span>Lead / campaign reference</span>
              <input value={lead} onChange={(event) => setLead(event.target.value)} />
            </label>

            <label className="commercial-field commercial-field--full">
              <span>Attachments</span>
              <input type="file" multiple />
            </label>

            <label className="commercial-check commercial-field--full">
              <input
                type="checkbox"
                checked={consent}
                onChange={(event) => setConsent(event.target.checked)}
              />
              Client consent and privacy notice recorded
            </label>
          </div>
        </div>

        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button
            type="button"
            className="commercial-btn"
            disabled={saving}
            onClick={calculateEstimate}
          >
            Calculate Estimate
          </button>
          <button type="submit" className="commercial-btn commercial-btn-primary" disabled={saving}>
            {saving ? 'Submitting...' : 'Submit Request'}
          </button>
        </footer>
      </form>
    </div>
  )
}
