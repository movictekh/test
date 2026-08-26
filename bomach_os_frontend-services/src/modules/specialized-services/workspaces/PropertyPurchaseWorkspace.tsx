import { IconSearch, IconUserPlus, IconX } from '@tabler/icons-react'
import { useEffect, useMemo, useState } from 'react'
import { presentError } from '@/shared/errors'
import { formatCurrency } from '@/shared/lib/formatters'
import { propertyPurchaseApi } from '../real-estate/property-purchase.api'
import type {
  Estate,
  Property,
  PropertyPurchase,
  PurchaseClient,
  PurchaseMode,
} from '../real-estate/real-estate.types'

export function PropertyPurchaseWorkspace({
  estate,
  property,
  canCreateClient,
  onClose,
  onCreated,
}: {
  estate: Estate
  property: Property
  canCreateClient: boolean
  onClose: () => void
  onCreated: (purchase: PropertyPurchase) => void
}) {
  const [search, setSearch] = useState('')
  const [clients, setClients] = useState<PurchaseClient[]>([])
  const [selectedClient, setSelectedClient] = useState<PurchaseClient | null>(null)
  const [searching, setSearching] = useState(false)
  const [manualOpen, setManualOpen] = useState(false)
  const [creatingClient, setCreatingClient] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [company, setCompany] = useState('')
  const [sendPortalInvite, setSendPortalInvite] = useState(false)
  const [mode, setMode] = useState<PurchaseMode>('full_payment')
  const [agreedPrice, setAgreedPrice] = useState(String(property.price))
  const [months, setMonths] = useState(
    estate.maxInstallmentMonths ? String(Math.min(estate.maxInstallmentMonths, 6)) : '6',
  )

  const searchReady = search.trim().length >= 2
  useEffect(() => {
    if (!searchReady) return
    let cancelled = false
    const timer = window.setTimeout(() => {
      setSearching(true)
      void propertyPurchaseApi
        .searchClients(search)
        .then((results) => {
          if (!cancelled) setClients(results)
        })
        .catch((reason) => {
          if (!cancelled) setError(presentError(reason, 'background-action').message)
        })
        .finally(() => {
          if (!cancelled) setSearching(false)
        })
    }, 250)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [search, searchReady])

  const price = Number(agreedPrice)
  const installmentMonths = Number(months)
  const reservationPercent =
    mode !== 'full_payment' && estate.reservationAllowed ? estate.reservationThresholdPercent : null
  const reservationAmount = useMemo(() => {
    if (reservationPercent == null || !Number.isFinite(price) || price <= 0) return null
    return (price * reservationPercent) / 100
  }, [price, reservationPercent])

  const createClient = async () => {
    setError('')
    if (!firstName.trim() || !lastName.trim() || !email.trim()) {
      setError('First name, last name and email are required for a new client.')
      return
    }
    setCreatingClient(true)
    try {
      const client = await propertyPurchaseApi.createClient({
        firstName,
        lastName,
        email,
        phoneNumber: phone,
        companyName: company,
        sendPortalInvite,
      })
      setSelectedClient(client)
      setManualOpen(false)
    } catch (reason) {
      setError(presentError(reason, 'form-submit').message)
    } finally {
      setCreatingClient(false)
    }
  }

  const submit = async () => {
    setError('')
    if (!selectedClient) return setError('Select or create the purchaser first.')
    if (!Number.isFinite(price) || price <= 0)
      return setError('Agreed price must be greater than zero.')
    if (mode === 'installment' && (!Number.isInteger(installmentMonths) || installmentMonths < 1)) {
      return setError('Choose a positive installment duration.')
    }
    if (
      mode === 'installment' &&
      estate.maxInstallmentMonths != null &&
      installmentMonths > estate.maxInstallmentMonths
    )
      return setError(`This Estate allows at most ${estate.maxInstallmentMonths} months.`)

    setSaving(true)
    try {
      onCreated(
        await propertyPurchaseApi.createPurchase({
          propertyId: property.id,
          clientId: selectedClient.id,
          mode,
          agreedPrice: price,
          installmentMonths: mode === 'installment' ? installmentMonths : null,
        }),
      )
    } catch (reason) {
      setError(presentError(reason, 'form-submit').message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="commercial-modal commercial-modal--xl specialized-real-estate-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Start property purchase"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Start Property Purchase</h2>
            <p>
              {property.propertyName} · {estate.estateName}
            </p>
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
          {error ? <div className="commercial-notice commercial-notice-red">{error}</div> : null}
          <section className="commercial-form-section">
            <div className="commercial-form-section-heading">
              <div>
                <h3>Purchaser</h3>
                <p>Search existing CRM clients by name, email, phone or company.</p>
              </div>
            </div>
            {selectedClient ? (
              <div className="commercial-notice">
                <strong>{selectedClient.fullName}</strong>
                <div>{selectedClient.email}</div>
                <small>
                  {[selectedClient.phone, selectedClient.companyName].filter(Boolean).join(' · ')}
                </small>
                <button
                  type="button"
                  className="specialized-btn specialized-btn-small"
                  onClick={() => setSelectedClient(null)}
                >
                  Change purchaser
                </button>
              </div>
            ) : (
              <>
                <label className="commercial-search">
                  <IconSearch size={14} />
                  <input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search CRM clients"
                  />
                </label>
                {searchReady ? (
                  <div className="specialized-table-wrap">
                    <table className="specialized-table">
                      <thead>
                        <tr>
                          <th>Client</th>
                          <th>Phone</th>
                          <th>Company</th>
                          <th />
                        </tr>
                      </thead>
                      <tbody>
                        {clients.map((client) => (
                          <tr key={client.id}>
                            <td>
                              <b>{client.fullName}</b>
                              <small>{client.email}</small>
                            </td>
                            <td>{client.phone || '—'}</td>
                            <td>{client.companyName || '—'}</td>
                            <td>
                              <button
                                type="button"
                                className="specialized-btn specialized-btn-small"
                                onClick={() => setSelectedClient(client)}
                              >
                                Select
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {searching ? <div className="commercial-notice">Searching clients…</div> : null}
                  </div>
                ) : (
                  <div className="commercial-notice">Enter at least two characters to search.</div>
                )}
                {canCreateClient ? (
                  <button
                    type="button"
                    className="specialized-btn"
                    onClick={() => setManualOpen((value) => !value)}
                  >
                    <IconUserPlus size={14} />{' '}
                    {manualOpen ? 'Hide new client form' : 'Create purchaser manually'}
                  </button>
                ) : null}
              </>
            )}
          </section>

          {!selectedClient && manualOpen && canCreateClient ? (
            <section className="commercial-form-section">
              <div className="commercial-form-section-heading">
                <div>
                  <h3>New CRM Client</h3>
                  <p>No portal credentials or email are created unless explicitly requested.</p>
                </div>
              </div>
              <div className="commercial-form-grid">
                <label className="commercial-field">
                  <span>First name</span>
                  <input value={firstName} onChange={(e) => setFirstName(e.target.value)} />
                </label>
                <label className="commercial-field">
                  <span>Last name</span>
                  <input value={lastName} onChange={(e) => setLastName(e.target.value)} />
                </label>
                <label className="commercial-field">
                  <span>Email</span>
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
                </label>
                <label className="commercial-field">
                  <span>Phone</span>
                  <input value={phone} onChange={(e) => setPhone(e.target.value)} />
                </label>
                <label className="commercial-field">
                  <span>Company</span>
                  <input value={company} onChange={(e) => setCompany(e.target.value)} />
                </label>
              </div>
              <label className="commercial-checkbox-card">
                <input
                  type="checkbox"
                  checked={sendPortalInvite}
                  onChange={(e) => setSendPortalInvite(e.target.checked)}
                />
                <span>
                  <strong>Send client-portal invite</strong>
                  <small>Off by default.</small>
                </span>
              </label>
              <button
                type="button"
                className="specialized-btn specialized-btn-primary"
                disabled={creatingClient}
                onClick={() => void createClient()}
              >
                {creatingClient ? 'Creating client…' : 'Create and select client'}
              </button>
            </section>
          ) : null}

          <section className="commercial-form-section">
            <div className="commercial-form-section-heading">
              <div>
                <h3>Purchase terms</h3>
                <p>
                  Phase 3 records agreement terms only; verified payment later changes property
                  state.
                </p>
              </div>
            </div>
            <label className="commercial-field">
              <span>Purchase mode</span>
              <select value={mode} onChange={(e) => setMode(e.target.value as PurchaseMode)}>
                <option value="full_payment">Full payment</option>
                {estate.reservationAllowed ? (
                  <option value="reservation">Reservation</option>
                ) : null}
                {estate.installmentAllowed ? (
                  <option value="installment">Installment</option>
                ) : null}
              </select>
            </label>
            <label className="commercial-field">
              <span>Agreed price</span>
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={agreedPrice}
                onChange={(e) => setAgreedPrice(e.target.value)}
              />
            </label>
            {mode === 'installment' ? (
              <label className="commercial-field">
                <span>Installment months</span>
                <input
                  type="number"
                  min="1"
                  max={estate.maxInstallmentMonths ?? undefined}
                  value={months}
                  onChange={(e) => setMonths(e.target.value)}
                />
              </label>
            ) : null}
            <div className="specialized-data-studio-summary">
              <article>
                <span>Agreed price</span>
                <strong>{price > 0 ? formatCurrency(price) : '—'}</strong>
              </article>
              <article>
                <span>Reservation threshold</span>
                <strong>{reservationPercent == null ? '—' : `${reservationPercent}%`}</strong>
              </article>
              <article>
                <span>Reservation amount</span>
                <strong>
                  {reservationAmount == null ? '—' : formatCurrency(reservationAmount)}
                </strong>
              </article>
              <article>
                <span>Payment window</span>
                <strong>{estate.reservationPaymentWindowHours}h</strong>
              </article>
            </div>
            <div className="commercial-notice">
              New purchase status: <strong>Awaiting approval</strong>. No invoice, reservation,
              ownership transfer or Finance posting occurs in Phase 3.
            </div>
          </section>
        </div>
        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" disabled={saving} onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="commercial-btn commercial-btn-primary"
            disabled={saving || !selectedClient}
            onClick={() => void submit()}
          >
            {saving ? 'Creating purchase…' : 'Create purchase'}
          </button>
        </footer>
      </section>
    </div>
  )
}
