import { IconExternalLink, IconRefresh, IconX } from '@tabler/icons-react'
import { useMemo, useState } from 'react'

import { presentError } from '@/shared/errors'
import { formatCurrency } from '@/shared/lib/formatters'

import { propertyPurchaseApi } from '../real-estate/property-purchase.api'
import type {
  PropertyPurchase,
  PropertyPurchasePaymentRequest,
} from '../real-estate/real-estate.types'

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function text(value: unknown) {
  return typeof value === 'string' ? value : ''
}

function paymentAccount(request: PropertyPurchasePaymentRequest | null) {
  const dynamicInvoice = asRecord(request?.providerMetadata.dynamic_invoice)
  return {
    accountNumber: text(dynamicInvoice.accountNumber ?? dynamicInvoice.account_number),
    bankName: text(dynamicInvoice.bankName ?? dynamicInvoice.bank_name),
    accountName: text(dynamicInvoice.accountName ?? dynamicInvoice.account_name),
  }
}

export function PropertyPurchaseLifecycleWorkspace({
  purchase,
  canManage,
  onClose,
  onChanged,
}: {
  purchase: PropertyPurchase
  canManage: boolean
  onClose: () => void
  onChanged: (purchase: PropertyPurchase) => Promise<void> | void
}) {
  const [current, setCurrent] = useState(purchase)
  const [payment, setPayment] = useState<PropertyPurchasePaymentRequest | null>(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')

  const outstanding = Math.max(0, current.agreedPrice - current.amountPaid)
  const account = paymentAccount(payment)
  const progress = useMemo(
    () =>
      current.agreedPrice > 0
        ? Math.min(100, Math.round((current.amountPaid / current.agreedPrice) * 100))
        : 0,
    [current.agreedPrice, current.amountPaid],
  )

  // Backend services are authoritative for expiry/default timing.
  // Keeping actions available for their lifecycle states avoids render-time
  // clock reads; premature actions simply return the precise API validation.
  // Backend services are authoritative for expiry/default timing.
  // Keeping actions available for their lifecycle states avoids render-time
  // clock reads; premature actions simply return the precise API validation.
  const expireReady = current.status === 'awaiting_payment'
  const defaultReady = current.status === 'installment_active'

  const updatePurchase = async (next: PropertyPurchase) => {
    setCurrent(next)
    await onChanged(next)
  }

  const runPurchaseAction = async (action: string, operation: () => Promise<PropertyPurchase>) => {
    setBusy(action)
    setError('')
    try {
      await updatePurchase(await operation())
      setPayment(null)
    } catch (reason) {
      setError(presentError(reason, 'form-submit').message)
    } finally {
      setBusy('')
    }
  }

  const refresh = async () => {
    setBusy('refresh')
    setError('')
    try {
      await updatePurchase(await propertyPurchaseApi.getPurchase(current.id))
    } catch (reason) {
      setError(presentError(reason, 'background-action').message)
    } finally {
      setBusy('')
    }
  }

  const createPayment = async () => {
    setBusy('payment')
    setError('')
    try {
      setPayment(await propertyPurchaseApi.createPaymentRequest(current.id))
    } catch (reason) {
      setError(presentError(reason, 'form-submit').message)
    } finally {
      setBusy('')
    }
  }

  return (
    <div
      className="commercial-modal-backdrop commercial-modal-backdrop--nested"
      role="presentation"
      onMouseDown={onClose}
    >
      <section
        className="commercial-modal commercial-modal--xl specialized-real-estate-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Manage property purchase"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Property Purchase</h2>
            <p>
              {current.propertyName} · {current.clientName}
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
                <h3>Settlement status</h3>
                <p>Only verified Central Payments receipts can reserve or sell this property.</p>
              </div>
            </div>

            <div className="specialized-data-studio-summary">
              <article>
                <span>Status</span>
                <strong>{current.status.replaceAll('_', ' ')}</strong>
              </article>
              <article>
                <span>Agreed price</span>
                <strong>{formatCurrency(current.agreedPrice)}</strong>
              </article>
              <article>
                <span>Verified paid</span>
                <strong>{formatCurrency(current.amountPaid)}</strong>
              </article>
              <article>
                <span>Outstanding</span>
                <strong>{formatCurrency(outstanding)}</strong>
              </article>
            </div>

            <div className="commercial-notice">
              Payment progress: <strong>{progress}%</strong>
              {current.reservationAmount != null ? (
                <>
                  {' '}
                  · Reservation threshold{' '}
                  <strong>{formatCurrency(current.reservationAmount)}</strong>
                </>
              ) : null}
            </div>

            {current.paymentWindowExpiresAt ? (
              <div className="commercial-notice">
                Initial payment deadline:{' '}
                <strong>{new Date(current.paymentWindowExpiresAt).toLocaleString()}</strong>
              </div>
            ) : null}

            {current.nextPaymentDueAt ? (
              <div className="commercial-notice">
                Next installment due:{' '}
                <strong>{new Date(current.nextPaymentDueAt).toLocaleString()}</strong> ·{' '}
                {current.paymentWindowHours}h grace window
              </div>
            ) : null}
          </section>

          {payment ? (
            <section className="commercial-form-section">
              <div className="commercial-form-section-heading">
                <div>
                  <h3>Payment request</h3>
                  <p>
                    {payment.provider} · {formatCurrency(payment.amount)} {payment.currency}
                  </p>
                </div>
              </div>

              {account.accountNumber ? (
                <div className="commercial-notice">
                  <strong>{account.bankName || 'Bank transfer account'}</strong>
                  <div>{account.accountNumber}</div>
                  {account.accountName ? <small>{account.accountName}</small> : null}
                </div>
              ) : null}

              {payment.checkoutUrl ? (
                <a
                  className="specialized-btn specialized-btn-primary"
                  href={payment.checkoutUrl}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open Monnify checkout
                  <IconExternalLink size={13} />
                </a>
              ) : (
                <div className="commercial-notice">
                  Payment request exists. Refresh and retry if provider checkout details are still
                  being initialized.
                </div>
              )}
            </section>
          ) : null}

          <section className="commercial-form-section">
            <div className="commercial-form-section-heading">
              <div>
                <h3>Actions</h3>
                <p>Approval makes the agreement payable; verified money controls property state.</p>
              </div>
            </div>

            <div className="commercial-modal-footer">
              <button
                type="button"
                className="commercial-btn"
                disabled={Boolean(busy)}
                onClick={() => void refresh()}
              >
                <IconRefresh size={13} />
                Refresh status
              </button>

              {current.status === 'awaiting_approval' ? (
                <button
                  type="button"
                  className="commercial-btn commercial-btn-primary"
                  disabled={!canManage || Boolean(busy)}
                  onClick={() =>
                    void runPurchaseAction('approve', () =>
                      propertyPurchaseApi.approvePurchase(current.id),
                    )
                  }
                >
                  {busy === 'approve' ? 'Approving…' : 'Approve for payment'}
                </button>
              ) : null}

              {['awaiting_payment', 'reserved', 'installment_active'].includes(current.status) ? (
                <button
                  type="button"
                  className="commercial-btn commercial-btn-primary"
                  disabled={!canManage || Boolean(busy)}
                  onClick={() => void createPayment()}
                >
                  {busy === 'payment' ? 'Creating request…' : 'Create next payment request'}
                </button>
              ) : null}

              {current.status === 'awaiting_approval' ||
              (current.status === 'awaiting_payment' && current.amountPaid === 0) ? (
                <button
                  type="button"
                  className="commercial-btn"
                  disabled={!canManage || Boolean(busy)}
                  onClick={() =>
                    void runPurchaseAction('cancel', () =>
                      propertyPurchaseApi.cancelPurchase(current.id),
                    )
                  }
                >
                  {busy === 'cancel' ? 'Cancelling…' : 'Cancel unpaid purchase'}
                </button>
              ) : null}

              {expireReady ? (
                <button
                  type="button"
                  className="commercial-btn"
                  disabled={!canManage || Boolean(busy)}
                  onClick={() =>
                    void runPurchaseAction('expire', () =>
                      propertyPurchaseApi.expirePurchase(current.id),
                    )
                  }
                >
                  {busy === 'expire' ? 'Expiring…' : 'Expire unpaid purchase'}
                </button>
              ) : null}

              {defaultReady ? (
                <button
                  type="button"
                  className="commercial-btn"
                  disabled={!canManage || Boolean(busy)}
                  onClick={() =>
                    void runPurchaseAction('default', () =>
                      propertyPurchaseApi.defaultPurchase(current.id),
                    )
                  }
                >
                  {busy === 'default' ? 'Updating…' : 'Mark overdue installment defaulted'}
                </button>
              ) : null}
            </div>

            {current.amountPaid > 0 && current.status !== 'fully_paid' ? (
              <div className="commercial-notice">
                Cancellation is disabled after verified money. Refund/reconciliation must be
                completed before commercial release.
              </div>
            ) : null}
          </section>
        </div>
      </section>
    </div>
  )
}
