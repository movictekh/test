import type {
  FieldTypeDto,
  RequestFormDto,
  RequestFormInputDto,
  RequestFormUpdateDto,
} from '../api/service-administration.contracts'
import type {
  RequestFieldTypeOption,
  RequestFormField,
  SaveRequestFormInput,
  ServiceRequestForm,
} from '../types/service-administration.types'

const backendFieldTypes = new Set<RequestFormField['type']>([
  'text',
  'textarea',
  'number',
  'money',
  'date',
  'select',
  'multiselect',
  'checkbox',
  'file',
  'location',
  'email',
  'phone',
])

function normalizeFieldType(value: string): RequestFormField['type'] {
  return backendFieldTypes.has(value as RequestFormField['type'])
    ? (value as RequestFormField['type'])
    : 'text'
}

function normalizeDomainStatus(status: string): ServiceRequestForm['status'] {
  if (status === 'active' || status === 'draft') return status
  return 'inactive'
}

function backendFormStatus(
  status: SaveRequestFormInput['status'],
): 'active' | 'draft' | 'archived' {
  return status === 'inactive' ? 'archived' : status
}

export function mapFieldTypeDto(dto: FieldTypeDto): RequestFieldTypeOption {
  return {
    value: normalizeFieldType(dto.value),
    label: dto.label,
    supportsOptions: dto.supports_options,
    supportsValidation: dto.supports_validation,
  }
}

export function mapRequestFormDto(dto: RequestFormDto, serviceName: string): ServiceRequestForm {
  return {
    id: String(dto.id),
    name: dto.name,
    serviceId: String(dto.service_id),
    serviceName,
    status: normalizeDomainStatus(dto.status),
    version: dto.version,
    fields: (dto.fields ?? [])
      .slice()
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((field) => ({
        id: String(field.id),
        label: field.label,
        key: field.key,
        type: normalizeFieldType(field.field_type),
        required: field.required,
        ...(field.help_text ? { helpText: field.help_text } : {}),
        ...(field.options.length ? { options: field.options.map((option) => String(option)) } : {}),
      })),
    updatedAt: dto.updated_at,
  }
}

export function mapSaveRequestFormInput(
  input: SaveRequestFormInput,
): RequestFormInputDto | RequestFormUpdateDto {
  return {
    name: input.name,
    status: backendFormStatus(input.status),
    is_active: input.status === 'active',
    fields: input.fields.map((field, index) => ({
      key: field.key,
      label: field.label,
      field_type: field.type,
      required: field.required,
      options: field.options ?? [],
      validation: {},
      help_text: field.helpText ?? '',
      placeholder: '',
      sort_order: index,
    })),
  }
}
