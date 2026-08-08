import type {
  PricingConfigDto,
  PricingConfigInputDto,
  PricingConfigUpdateDto,
} from '../api/service-administration.contracts'
import type {
  CalculatorCharge,
  CalculatorVariable,
  PricingCalculator,
  PricingType,
  SaveCalculatorInput,
} from '../types/service-administration.types'

function numberValue(value: string | number): number {
  return Number(value) || 0
}

function normalizePricingType(value: string): PricingType {
  if (
    value === 'fixed' ||
    value === 'unit_rate' ||
    value === 'area_rate' ||
    value === 'percentage' ||
    value === 'formula'
  ) {
    return value
  }
  return 'fixed'
}

function pricingStatus(status: string): PricingCalculator['status'] {
  return status === 'active' || status === 'draft' ? status : 'inactive'
}

function domainVariableType(fieldType: string): CalculatorVariable['type'] {
  if (fieldType === 'checkbox') return 'boolean'
  if (fieldType === 'select' || fieldType === 'multiselect') return 'select'
  return 'number'
}

export function mapPricingConfigDto(dto: PricingConfigDto): PricingCalculator {
  const charges: CalculatorCharge[] = []

  if (dto.formula) {
    charges.push({
      id: `formula-${dto.id}`,
      label: 'Formula',
      kind: 'formula',
      value: dto.formula,
    })
  }

  charges.push(
    {
      id: `deposit-${dto.id}`,
      label: 'Deposit',
      kind: 'percentage',
      value: numberValue(dto.deposit_percent),
    },
    {
      id: `tax-${dto.id}`,
      label: 'Tax',
      kind: 'percentage',
      value: numberValue(dto.tax_rate),
    },
    {
      id: `approval-${dto.id}`,
      label: 'Discount approval',
      kind: 'percentage',
      value: numberValue(dto.discount_approval_threshold_percent),
    },
  )

  const variables: CalculatorVariable[] = (dto.fields ?? [])
    .slice()
    .sort((a, b) => a.sort_order - b.sort_order)
    .map((field) => ({
      id: String(field.id),
      label: field.label,
      key: field.key,
      type: domainVariableType(field.field_type),
      ...(field.default_value !== null && field.default_value !== undefined
        ? {
            unit:
              typeof field.default_value === 'string' ||
              typeof field.default_value === 'number' ||
              typeof field.default_value === 'boolean'
                ? String(field.default_value)
                : JSON.stringify(field.default_value),
          }
        : {}),
    }))

  return {
    id: String(dto.id),
    name: dto.name,
    code: `CALC-${dto.id}`,
    serviceId: String(dto.service_id),
    serviceName: dto.service_name,
    description: `${dto.pricing_type} pricing configuration`,
    pricingType: normalizePricingType(dto.pricing_type),
    status: pricingStatus(dto.status),
    version: dto.version,
    variables,
    charges,
    sampleTotal: 0,
    updatedAt: dto.updated_at,
  }
}

function percentage(input: SaveCalculatorInput, keyword: string): number {
  const value = input.charges.find((charge) => charge.label.toLowerCase().includes(keyword))?.value
  return typeof value === 'number' ? value : Number(value) || 0
}

export function mapSaveCalculatorInput(
  input: SaveCalculatorInput,
): PricingConfigInputDto | PricingConfigUpdateDto {
  const pricingType = input.pricingType ?? 'fixed'
  const formula =
    pricingType === 'formula'
      ? (input.charges.find((charge) => charge.kind === 'formula')?.value ?? '')
      : ''

  return {
    name: input.name,
    pricing_type: pricingType,
    formula: String(formula),
    tax_rate: percentage(input, 'tax'),
    deposit_percent: percentage(input, 'deposit'),
    discount_approval_threshold_percent: percentage(input, 'approval'),
    status: input.status === 'inactive' ? 'archived' : input.status,
    is_active: input.status === 'active',
    fields: input.variables.map((variable, index) => ({
      key: variable.key,
      label: variable.label,
      field_type:
        variable.type === 'boolean' ? 'checkbox' : variable.type === 'select' ? 'select' : 'number',
      default_value: variable.unit ?? null,
      required: true,
      options: [],
      validation: {},
      sort_order: index,
    })),
  }
}
