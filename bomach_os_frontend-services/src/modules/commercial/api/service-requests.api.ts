import { apiClient } from '@/shared/api/api-client'

import {
  mapClients,
  mapEmployees,
  mapIntakeForm,
  mapServicePricingConfig,
  mapServiceRequestChoices,
  mapServiceRequestDetail,
  mapServiceRequestList,
  mapServices,
} from './service-requests.mapper'
import type {
  ClientOption,
  CreateServiceRequestActivityInput,
  CreateServiceRequestAttachmentInput,
  CreateServiceRequestInput,
  EmployeeOption,
  PaginatedResult,
  ServicePricingConfig,
  ServiceIntakeForm,
  ServiceOption,
  ServiceRequestChoices,
  ServiceRequestDetail,
  ServiceRequestFilters,
  ServiceRequestListItem,
  ServiceRequestSummary,
  UpdateServiceRequestInput,
} from './service-requests.types'

function qs(filters: ServiceRequestFilters = {}) {
  const query = new URLSearchParams()
  const limit = filters.limit ?? 10
  const page = filters.page ?? 1
  query.set('limit', String(limit))
  query.set('offset', String((page - 1) * limit))
  if (filters.search) query.set('search', filters.search)
  if (filters.status) query.set('status', filters.status)
  if (filters.priority) query.set('priority', filters.priority)
  if (filters.branchId) query.set('branch_id', String(filters.branchId))
  if (filters.serviceId) query.set('service_id', String(filters.serviceId))
  return query.toString()
}

async function count(filters: ServiceRequestFilters = {}) {
  return mapServiceRequestList(
    await apiClient.get<unknown>(
      `/service-requests/admin?${qs({ ...filters, page: 1, limit: 1 })}`,
    ),
  ).count
}

export const serviceRequestsApi = {
  async list(
    filters: ServiceRequestFilters = {},
  ): Promise<PaginatedResult<ServiceRequestListItem>> {
    return mapServiceRequestList(
      await apiClient.get<unknown>(`/service-requests/admin?${qs(filters)}`),
    )
  },

  async detail(requestId: number): Promise<ServiceRequestDetail> {
    return mapServiceRequestDetail(
      await apiClient.get<unknown>(`/service-requests/admin/${requestId}`),
    )
  },

  async choices(): Promise<ServiceRequestChoices> {
    return mapServiceRequestChoices(await apiClient.get<unknown>('/service-requests/choices'))
  },

  async clients(): Promise<ClientOption[]> {
    return mapClients(await apiClient.get<unknown>('/clients/admin/clients'))
  },

  async services(): Promise<ServiceOption[]> {
    return mapServices(
      await apiClient.get<unknown>(
        '/services/catalogue?status=active&client_visibility=visible&limit=100&offset=0',
      ),
    )
  },

  async employees(): Promise<EmployeeOption[]> {
    return mapEmployees(
      await apiClient.get<unknown>('/employees/employees?is_active=true&limit=100&offset=0'),
    )
  },

  async intakeForm(serviceId: number): Promise<ServiceIntakeForm> {
    return mapIntakeForm(
      await apiClient.get<unknown>(`/service-requests/services/${serviceId}/intake-form`),
    )
  },

  async activePricingConfig(serviceId: number): Promise<ServicePricingConfig | null> {
    const list = await apiClient.get<unknown>(
      `/services/pricing-configs?service_id=${serviceId}&status=active&limit=1&offset=0`,
    )
    const items =
      typeof list === 'object' && list !== null
        ? (list as Record<string, unknown>).items
        : undefined
    const rows: unknown[] = Array.isArray(list) ? list : Array.isArray(items) ? items : []
    const first = rows[0]
    if (!first || typeof first !== 'object' || first === null) return null

    const configId = Number((first as { id?: unknown }).id)
    if (!Number.isFinite(configId) || configId <= 0) return null

    return mapServicePricingConfig(
      await apiClient.get<unknown>(`/services/${serviceId}/pricing-configs/${configId}`),
    )
  },

  async uploadFile(file: File, signal?: AbortSignal): Promise<string> {
    const formData = new FormData()
    formData.set('file', file)
    const payload = await apiClient.post<{ url: string }>('/others/upload-file', formData, {
      ...(signal ? { signal } : {}),
    })
    return payload.url
  },

  async summary(): Promise<ServiceRequestSummary> {
    const [total, newCount, underReview, awaitingClient, siteAssessment, high, critical] =
      await Promise.all([
        count(),
        count({ status: 'new' }),
        count({ status: 'under_review' }),
        count({ status: 'awaiting_client' }),
        count({ status: 'site_assessment' }),
        count({ priority: 'high' }),
        count({ priority: 'critical' }),
      ])
    return {
      total,
      newCount,
      underReview,
      awaitingClient,
      siteAssessment,
      highPriority: high + critical,
    }
  },

  async create(input: CreateServiceRequestInput): Promise<ServiceRequestDetail> {
    return mapServiceRequestDetail(
      await apiClient.post<unknown>('/service-requests/admin', {
        client_id: input.clientId,
        service_id: input.serviceId,
        ...(input.subserviceId ? { subservice_id: input.subserviceId } : {}),
        ...(input.branchId ? { branch_id: input.branchId } : {}),
        contact_name: input.contactName,
        contact_phone: input.contactPhone,
        contact_email: input.contactEmail,
        customer_type: input.customerType,
        source: input.source,
        source_reference: input.sourceReference,
        priority: input.priority,
        ...(input.budget !== undefined ? { budget: input.budget } : {}),
        estimated_value: input.estimatedValue,
        ...(input.preferredDate ? { preferred_date: input.preferredDate } : {}),
        ...(input.dueDate ? { due_date: input.dueDate } : {}),
        next_action: input.nextAction,
        scope_summary: input.scopeSummary,
        answers: input.answers,
      }),
    )
  },

  async update(requestId: number, input: UpdateServiceRequestInput) {
    return mapServiceRequestDetail(
      await apiClient.patch<unknown>(`/service-requests/admin/${requestId}`, {
        ...(input.status !== undefined ? { status: input.status } : {}),
        ...(input.priority !== undefined ? { priority: input.priority } : {}),
        ...(input.branchId !== undefined ? { branch_id: input.branchId } : {}),
        ...(input.ownerId !== undefined ? { owner_id: input.ownerId } : {}),
        ...(input.budget !== undefined ? { budget: input.budget } : {}),
        ...(input.dueDate !== undefined ? { due_date: input.dueDate } : {}),
        ...(input.nextAction !== undefined ? { next_action: input.nextAction } : {}),
        ...(input.estimatedValue !== undefined ? { estimated_value: input.estimatedValue } : {}),
        ...(input.scopeSummary !== undefined ? { scope_summary: input.scopeSummary } : {}),
      }),
    )
  },

  async addActivity(requestId: number, input: CreateServiceRequestActivityInput) {
    await apiClient.post(`/service-requests/admin/${requestId}/activities`, {
      activity_type: input.activityType,
      outcome: input.outcome,
      note: input.note,
      next_action: input.nextAction ?? '',
      next_follow_up_at: input.nextFollowUpAt ?? null,
    })
  },

  async addAttachment(requestId: number, input: CreateServiceRequestAttachmentInput) {
    await apiClient.post(`/service-requests/admin/${requestId}/attachments`, {
      field_key: input.fieldKey ?? '',
      label: input.label ?? '',
      file_name: input.fileName ?? '',
      file_url: input.fileUrl,
      content_type: input.contentType ?? '',
      file_size_bytes: input.fileSizeBytes ?? 0,
    })
  },
}
