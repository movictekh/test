export interface QuotationPricingInput {
  serviceFee: number
  otherCharges: number
  discount: number
  taxRate: number
  depositPercent: number
}

export function calculateQuotationPreview(input: QuotationPricingInput) {
  const subtotal = Math.max(0, input.serviceFee) + Math.max(0, input.otherCharges)
  const discount = Math.max(0, input.discount)
  const taxable = Math.max(subtotal - discount, 0)
  const taxAmount = taxable * (Math.max(0, input.taxRate) / 100)
  const amount = taxable + taxAmount
  const depositAmount = amount * (Math.max(0, input.depositPercent) / 100)
  return { subtotal, taxable, taxAmount, amount, depositAmount }
}

export function validateQuotationPricing(input: QuotationPricingInput) {
  const errors: Partial<Record<keyof QuotationPricingInput, string>> = {}
  const subtotal = Number(input.serviceFee) + Number(input.otherCharges)
  if (!Number.isFinite(input.serviceFee) || input.serviceFee <= 0)
    errors.serviceFee = 'Service fee must be greater than zero.'
  if (!Number.isFinite(input.otherCharges) || input.otherCharges < 0)
    errors.otherCharges = 'Other charges cannot be negative.'
  if (!Number.isFinite(input.discount) || input.discount < 0)
    errors.discount = 'Discount cannot be negative.'
  else if (input.discount > subtotal) errors.discount = 'Discount cannot exceed subtotal.'
  if (!Number.isFinite(input.taxRate) || input.taxRate < 0 || input.taxRate > 100)
    errors.taxRate = 'Tax must be between 0 and 100.'
  if (
    !Number.isFinite(input.depositPercent) ||
    input.depositPercent < 0 ||
    input.depositPercent > 100
  )
    errors.depositPercent = 'Deposit must be between 0 and 100.'
  return errors
}
