import type {
  IntakeField,
  ServicePricingConfig,
  ServiceRequestPriority,
} from '../api/service-requests.types'

import type { PendingUpload } from './request-intake.types'

export interface AutoAnswerContext {
  contactName: string
  contactPhone: string
  contactEmail: string
  customerType: string
  budget: number
  preferredDate: string
  uploads: PendingUpload[]
}

export function missing(value: unknown) {
  return value == null || value === '' || (Array.isArray(value) && value.length === 0)
}

function normalizeToken(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}

function fieldToken(field: IntakeField) {
  return normalizeToken(`${field.key} ${field.label}`)
}

export function isClientIdentityField(field: IntakeField) {
  const token = fieldToken(field)
  return token.includes('client identity') || token.includes('client name')
}

export function isPhoneEmailField(field: IntakeField) {
  const token = fieldToken(field)
  return token.includes('phone') && token.includes('email')
}

export function isPhoneField(field: IntakeField) {
  const token = fieldToken(field)
  return field.fieldType === 'phone' || (token.includes('phone') && !token.includes('email'))
}

export function isEmailField(field: IntakeField) {
  const token = fieldToken(field)
  return field.fieldType === 'email' || token === 'email' || token.includes('contact email')
}

export function isCustomerTypeField(field: IntakeField) {
  return fieldToken(field).includes('customer type')
}

export function isBudgetField(field: IntakeField) {
  return fieldToken(field) === 'budget' || fieldToken(field).endsWith(' budget')
}

export function isPreferredDateField(field: IntakeField) {
  return fieldToken(field).includes('preferred date')
}

export function isScopeField(field: IntakeField) {
  const token = fieldToken(field)
  return (
    token.includes('scope message') ||
    token.includes('scope details') ||
    token.includes('scope summary') ||
    token.includes('scope') ||
    token.includes('request details') ||
    token.includes('message')
  )
}

export function isAutoFilledField(field: IntakeField) {
  return (
    isClientIdentityField(field) ||
    isPhoneEmailField(field) ||
    isPhoneField(field) ||
    isEmailField(field) ||
    isCustomerTypeField(field) ||
    isBudgetField(field) ||
    isPreferredDateField(field)
  )
}

export function fieldTextValue(value: unknown) {
  return typeof value === 'string' || typeof value === 'number' ? String(value) : ''
}

export function isPriorityValue(value: string): value is ServiceRequestPriority {
  return value === 'normal' || value === 'high' || value === 'critical'
}

export function resolveAutoAnswer(field: IntakeField, context: AutoAnswerContext) {
  if (field.fieldType === 'file') {
    return context.uploads
      .filter((upload) => upload.fieldKey === field.key && upload.status === 'uploaded')
      .map((upload) => upload.fileUrl)
  }
  if (isClientIdentityField(field)) return context.contactName
  if (isPhoneEmailField(field)) {
    return [context.contactPhone, context.contactEmail].filter(Boolean).join(' · ')
  }
  if (isPhoneField(field)) return context.contactPhone
  if (isEmailField(field)) return context.contactEmail
  if (isCustomerTypeField(field)) return context.customerType
  if (isBudgetField(field)) return context.budget > 0 ? context.budget : ''
  if (isPreferredDateField(field)) return context.preferredDate
  return undefined
}

export function shouldHideAutoField(field: IntakeField, context: AutoAnswerContext) {
  if (!isAutoFilledField(field)) return false
  const resolved = resolveAutoAnswer(field, context)
  if (field.required && missing(resolved)) return false
  return true
}

export function nonNegativeNumber(value: string) {
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return 0
  return Math.max(0, parsed)
}

function toNumericValue(value: unknown) {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const cleaned = value.trim().replace(/,/g, '')
    if (cleaned === '') return null
    const parsed = Number(cleaned)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function normalizeMatchToken(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '')
}

function resolvePricingValue(
  pricingField: ServicePricingConfig['fields'][number],
  intakeFields: IntakeField[],
  answers: Record<string, unknown>,
  topLevel: AutoAnswerContext,
) {
  const direct = toNumericValue(answers[pricingField.key])
  if (direct != null) return direct

  const pricingTokens = new Set([
    normalizeMatchToken(pricingField.key),
    normalizeMatchToken(pricingField.label),
  ])

  for (const field of intakeFields) {
    const intakeTokens = [normalizeMatchToken(field.key), normalizeMatchToken(field.label)]
    if (!intakeTokens.some((token) => token && pricingTokens.has(token))) continue

    const resolved = shouldHideAutoField(field, topLevel)
      ? resolveAutoAnswer(field, topLevel)
      : answers[field.key]
    const numeric = toNumericValue(resolved)
    if (numeric != null) return numeric
  }

  return toNumericValue(pricingField.defaultValue)
}

function conventionalEstimate(
  pricingConfig: ServicePricingConfig,
  variables: Record<string, number>,
) {
  const findValue = (...keys: string[]) => {
    for (const key of keys) {
      const value = variables[key]
      if (Number.isFinite(value)) return value
    }
    return null
  }

  if (pricingConfig.pricingType === 'fixed') {
    return (
      findValue('amount', 'fixed_price', 'fixedprice', 'price', 'rate') ??
      Object.values(variables)[0] ??
      null
    )
  }

  if (pricingConfig.pricingType === 'percentage') {
    const baseAmount = findValue('base_amount', 'baseamount', 'amount', 'budget')
    const rate = findValue('rate', 'percentage', 'percent')
    return baseAmount != null && rate != null ? (baseAmount * rate) / 100 : null
  }

  if (pricingConfig.pricingType === 'unit_rate') {
    const quantity = findValue('quantity', 'units', 'count')
    const rate = findValue('rate', 'unit_rate', 'unitrate', 'price')
    return quantity != null && rate != null ? quantity * rate : null
  }

  if (pricingConfig.pricingType === 'area_rate') {
    const area = findValue('area', 'size', 'plot_size', 'plotsize', 'quantity')
    const rate = findValue('rate', 'area_rate', 'arearate', 'price')
    return area != null && rate != null ? area * rate : null
  }

  return null
}

function pricingNeedsFormula(pricingConfig: ServicePricingConfig) {
  return pricingConfig.pricingType === 'formula' || pricingConfig.formula.trim().length > 0
}

export function calculateEstimateTotal(
  pricingConfig: ServicePricingConfig,
  intakeFields: IntakeField[],
  answers: Record<string, unknown>,
  topLevel: AutoAnswerContext,
) {
  const numericVariables: Record<string, number> = {}

  for (const field of pricingConfig.fields) {
    const value = resolvePricingValue(field, intakeFields, answers, topLevel)
    if (value == null) {
      if (field.required) {
        return {
          supported: false as const,
          reason: `Missing ${field.label.toLowerCase()}.`,
        }
      }
      continue
    }
    numericVariables[field.key] = value
  }

  if (pricingNeedsFormula(pricingConfig)) {
    return {
      supported: false as const,
      reason:
        'This service uses an advanced calculator formula that cannot be resolved safely here yet.',
    }
  }

  const subtotal = conventionalEstimate(pricingConfig, numericVariables)

  if (subtotal == null || !Number.isFinite(subtotal)) {
    return {
      supported: false as const,
      reason: 'This calculator needs pricing rules that are not available in this request form.',
    }
  }

  const total = subtotal + subtotal * (pricingConfig.taxRate / 100)
  return {
    supported: true as const,
    total: Math.max(0, Number(total.toFixed(2))),
    subtotal: Math.max(0, Number(subtotal.toFixed(2))),
  }
}

export function validateAnswers(fields: IntakeField[], answers: Record<string, unknown>) {
  for (const field of fields) {
    const value = answers[field.key]
    if (field.required && missing(value)) return `${field.label} is required.`
    if (missing(value)) continue

    if (
      (field.fieldType === 'number' || field.fieldType === 'money') &&
      !Number.isFinite(Number(value))
    ) {
      return `${field.label} must be numeric.`
    }
  }
  return null
}

export function validateAnswerFields(fields: IntakeField[], answers: Record<string, unknown>) {
  const errors: Record<string, string> = {}

  for (const field of fields) {
    const value = answers[field.key]

    if (field.required && missing(value)) {
      errors[field.key] = `${field.label} is required.`
      continue
    }
    if (missing(value)) continue

    if (
      (field.fieldType === 'number' || field.fieldType === 'money') &&
      !Number.isFinite(Number(value))
    ) {
      errors[field.key] = `${field.label} must be numeric.`
    }
  }

  return errors
}

export function normalizeAnswers(fields: IntakeField[], answers: Record<string, unknown>) {
  return Object.fromEntries(
    fields.map((field) => {
      const value = answers[field.key]

      if (field.fieldType === 'number' || field.fieldType === 'money') {
        return [field.key, missing(value) ? null : Number(value)]
      }
      if (field.fieldType === 'checkbox') {
        return [field.key, Boolean(value)]
      }
      if (field.fieldType === 'multiselect') {
        return [field.key, Array.isArray(value) ? value : []]
      }
      if (field.fieldType === 'file') {
        return [field.key, Array.isArray(value) ? value : missing(value) ? [] : [value]]
      }

      return [field.key, value]
    }),
  )
}

export function firstScopeValue(fields: IntakeField[], answers: Record<string, unknown>) {
  const match = fields.find(isScopeField)
  const value = match ? answers[match.key] : null
  return typeof value === 'string' ? value.trim() : ''
}
