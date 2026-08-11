import type {
  ClientOption,
  EmployeeOption,
  IntakeField,
  PaginatedResult,
  ServicePricingConfig,
  ServiceIntakeForm,
  ServiceOption,
  ServiceRequestChoices,
  ServiceRequestDetail,
  ServiceRequestListItem,
} from './service-requests.types'

type JsonRecord = Record<string, unknown>

const record = (value: unknown): JsonRecord =>
  typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as JsonRecord) : {}

const text = (value: unknown, fallback = '') => (typeof value === 'string' ? value : fallback)

function num(value: unknown, fallback = 0) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

const nullableNumber = (value: unknown) => (value == null || value === '' ? null : num(value))

const nullableText = (value: unknown) => (value == null || value === '' ? null : text(value))

const array = (value: unknown): unknown[] => (Array.isArray(value) ? value : [])

function paginatedRows(payload: unknown) {
  if (Array.isArray(payload)) return { count: payload.length, rows: payload }
  const root = record(payload)
  const rows = Array.isArray(root.items)
    ? root.items
    : Array.isArray(root.results)
      ? root.results
      : Array.isArray(root.data)
        ? root.data
        : []
  return { count: num(root.count, rows.length), rows }
}

function snapshotBudget(value: JsonRecord) {
  const snapshot = record(value.answers_snapshot)
  const direct = nullableNumber(snapshot.budget)
  if (direct != null) return direct

  const answers = array(value.answers)
  for (const item of answers) {
    const row = record(item)
    const fieldKey = text(row.field_key).trim().toLowerCase()
    const label = text(row.label).trim().toLowerCase()
    if (fieldKey === 'budget' || label === 'budget') {
      const resolved = nullableNumber(row.value)
      if (resolved != null) return resolved
    }
  }

  return null
}

export function mapServiceRequestListItem(payload: unknown): ServiceRequestListItem {
  const value = record(payload)
  return {
    id: num(value.id),
    requestNumber: text(value.request_number),
    clientId: num(value.client_id),
    clientName: text(value.client_name),
    serviceId: num(value.service_id),
    serviceName: text(value.service_name),
    subserviceId: nullableNumber(value.subservice_id),
    subserviceName: text(value.subservice_name),
    branchId: nullableNumber(value.branch_id),
    branchName: text(value.branch_name),
    quoteId: nullableNumber(value.quote_id),
    quoteNumber: text(value.quote_number),
    contactName: text(value.contact_name),
    contactPhone: text(value.contact_phone),
    contactEmail: text(value.contact_email),
    customerType: text(value.customer_type),
    source: text(value.source),
    sourceReference: text(value.source_reference),
    status: text(value.status, 'new') as ServiceRequestListItem['status'],
    statusDisplay: text(value.status_display, text(value.status)),
    priority: text(value.priority, 'normal') as ServiceRequestListItem['priority'],
    budget: nullableNumber(value.budget),
    estimatedValue: num(value.estimated_value),
    preferredDate: nullableText(value.preferred_date),
    dueDate: nullableText(value.due_date),
    nextAction: text(value.next_action),
    scopeSummary: text(value.scope_summary),
    ownerId: nullableNumber(value.owner_id),
    ownerName: text(value.owner_name),
    createdAt: text(value.created_at),
    updatedAt: text(value.updated_at),
  }
}

export function mapServiceRequestDetail(payload: unknown): ServiceRequestDetail {
  const value = record(payload)
  const detail = mapServiceRequestListItem(payload)
  const resolvedBudget = detail.budget ?? snapshotBudget(value)
  return {
    ...detail,
    budget: resolvedBudget,
    serviceLeadId: nullableNumber(value.service_lead_id),
    crmLeadId: nullableNumber(value.crm_lead_id),
    requestFormId: num(value.request_form_id),
    requestFormVersion: num(value.request_form_version),
    pricingConfigId: nullableNumber(value.pricing_config_id),
    pricingConfigVersion: nullableNumber(value.pricing_config_version),
    workflowId: nullableNumber(value.workflow_id),
    workflowVersion: nullableNumber(value.workflow_version),
    answersSnapshot: record(value.answers_snapshot),
    formSnapshot: record(value.form_snapshot),
    answers: array(value.answers).map((item) => {
      const row = record(item)
      return {
        id: num(row.id),
        fieldKey: text(row.field_key),
        label: text(row.label),
        fieldType: text(row.field_type),
        value: row.value,
        sortOrder: num(row.sort_order),
      }
    }),
    attachments: array(value.attachments).map((item) => {
      const row = record(item)
      return {
        id: num(row.id),
        fieldKey: text(row.field_key),
        label: text(row.label),
        fileName: text(row.file_name),
        fileUrl: text(row.file_url),
        contentType: text(row.content_type),
        fileSizeBytes: num(row.file_size_bytes),
        uploadedById: nullableNumber(row.uploaded_by_id),
        createdAt: text(row.created_at),
      }
    }),
    activities: array(value.activities).map((item) => {
      const row = record(item)
      return {
        id: num(row.id),
        activityType: text(row.activity_type),
        activityTypeDisplay: text(row.activity_type_display, text(row.activity_type)),
        outcome: text(row.outcome),
        outcomeDisplay: text(row.outcome_display, text(row.outcome)),
        note: text(row.note),
        nextAction: text(row.next_action),
        nextFollowUpAt: nullableText(row.next_follow_up_at),
        createdById: nullableNumber(row.created_by_id),
        createdByName: text(row.created_by_name),
        createdAt: text(row.created_at),
      }
    }),
  }
}

export function mapServiceRequestList(payload: unknown): PaginatedResult<ServiceRequestListItem> {
  const { count, rows } = paginatedRows(payload)
  return { count, items: rows.map(mapServiceRequestListItem) }
}

function mapChoiceGroup(payload: unknown, key: string) {
  return array(record(payload)[key]).map((item) => {
    const row = record(item)
    return { value: text(row.value), label: text(row.label, text(row.value)) }
  })
}

export function mapServiceRequestChoices(payload: unknown): ServiceRequestChoices {
  return {
    statuses: mapChoiceGroup(payload, 'statuses'),
    priorities: mapChoiceGroup(payload, 'priorities'),
    sources: mapChoiceGroup(payload, 'sources'),
    customerTypes: mapChoiceGroup(payload, 'customer_types'),
    activityTypes: mapChoiceGroup(payload, 'activity_types'),
    activityOutcomes: mapChoiceGroup(payload, 'activity_outcomes'),
  }
}

export function mapClients(payload: unknown): ClientOption[] {
  const { rows } = paginatedRows(payload)
  return rows.map((item) => {
    const row = record(item)
    return {
      id: num(row.id),
      name:
        text(row.company_name) ||
        text(row.full_name) ||
        [text(row.first_name), text(row.last_name)].filter(Boolean).join(' ') ||
        text(row.email),
      email: text(row.email),
      phone: text(row.phone) || text(row.phone_number),
      companyName: text(row.company_name),
      active: row.is_active !== false,
    }
  })
}

export function mapServices(payload: unknown): ServiceOption[] {
  const { rows } = paginatedRows(payload)
  return rows.map((item) => {
    const row = record(item)
    return {
      id: num(row.id),
      code: text(row.code),
      name: text(row.name),
      division: text(row.division),
      activeBranches: array(row.active_branches).map((item) => {
        const branch = record(item)
        return {
          id: num(branch.branch_id ?? branch.id),
          name: text(branch.branch_name) || text(branch.name),
        }
      }),
    }
  })
}

export function mapEmployees(payload: unknown): EmployeeOption[] {
  const { rows } = paginatedRows(payload)
  return rows.map((item) => {
    const row = record(item)
    return {
      id: num(row.id),
      name:
        [text(row.first_name), text(row.last_name)].filter(Boolean).join(' ') ||
        text(row.email) ||
        text(row.employee_id),
      roleName: text(row.role_name),
      branchName: text(row.branch_name),
    }
  })
}

function mapOptions(value: unknown) {
  return array(value).map((item) => {
    if (typeof item === 'string' || typeof item === 'number') {
      const option = String(item)
      return { value: option, label: option }
    }
    const row = record(item)
    const raw = row.value ?? row.key ?? row.id ?? row.label
    const fallback = typeof raw === 'string' || typeof raw === 'number' ? String(raw) : ''
    return { value: fallback, label: text(row.label, fallback) }
  })
}

export function mapServicePricingConfig(payload: unknown): ServicePricingConfig {
  const row = record(payload)
  return {
    id: num(row.id),
    serviceId: num(row.service_id),
    serviceName: text(row.service_name),
    name: text(row.name),
    version: num(row.version, 1),
    pricingType: text(row.pricing_type),
    formula: text(row.formula),
    taxRate: num(row.tax_rate),
    depositPercent: num(row.deposit_percent),
    discountApprovalThresholdPercent: num(row.discount_approval_threshold_percent),
    status: text(row.status),
    active: row.is_active === true,
    fieldCount: num(row.field_count),
    fields: array(row.fields)
      .map((item) => {
        const field = record(item)
        return {
          id: num(field.id),
          key: text(field.key),
          label: text(field.label),
          fieldType: text(field.field_type),
          defaultValue: field.default_value,
          required: field.required === true,
          options: mapOptions(field.options),
          validation: record(field.validation),
          sortOrder: num(field.sort_order),
        }
      })
      .sort((left, right) => left.sortOrder - right.sortOrder),
  }
}

function mapField(payload: unknown): IntakeField {
  const row = record(payload)
  return {
    id: num(row.id),
    key: text(row.key),
    label: text(row.label),
    fieldType: text(row.field_type),
    required: row.required === true,
    options: mapOptions(row.options),
    validation: record(row.validation),
    helpText: text(row.help_text),
    placeholder: text(row.placeholder),
    sortOrder: num(row.sort_order),
  }
}

export function mapIntakeForm(payload: unknown): ServiceIntakeForm {
  const root = record(payload)
  const service = record(root.service)
  const form = record(root.active_request_form)
  return {
    service: {
      id: num(service.id),
      code: text(service.code),
      name: text(service.name),
      division: text(service.division),
      defaultSlaDays: num(service.default_sla_days),
      fulfillmentMode: text(service.fulfillment_mode),
    },
    form: {
      id: num(form.id),
      name: text(form.name),
      version: num(form.version),
      status: text(form.status),
      active: form.is_active === true,
      fields: array(form.fields).map(mapField),
    },
    subservices: array(root.subservices).map((item) => {
      const row = record(item)
      return {
        id: num(row.id),
        code: text(row.code),
        name: text(row.name),
        description: text(row.description),
        status: text(row.status),
      }
    }),
  }
}
