import { apiClient } from '@/shared/api/api-client'

import type {
  BranchActivationDto,
  BranchDto,
  BranchActivationInputDto,
  BranchActivationMatrixFilters,
  FieldTypeDto,
  LimitOffsetPageDto,
  MessageDto,
  PricingConfigDto,
  PricingConfigInputDto,
  PricingConfigListFilters,
  PricingConfigUpdateDto,
  RequestFormDto,
  RequestFormInputDto,
  RequestFormUpdateDto,
  RoleDto,
  ServiceCatalogueCardDto,
  ServiceCatalogueDetailDto,
  ServiceCategoryDto,
  ServiceCoreDto,
  ServiceCreateDto,
  ServiceListFilters,
  ServicePublishDto,
  ServiceSubserviceDto,
  ServiceSubserviceInputDto,
  ServiceSubserviceUpdateDto,
  ServiceUpdateDto,
  WorkflowDto,
  WorkflowInputDto,
  WorkflowSeedInputDto,
  WorkflowStageDto,
  WorkflowStageInputDto,
  WorkflowStageUpdateDto,
  WorkflowUpdateDto,
} from './service-administration.contracts'

const basePath = '/services'

function withQuery(
  path: string,
  params: Record<string, string | number | boolean | undefined>,
): string {
  const search = new URLSearchParams()

  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') {
      search.set(key, String(value))
    }
  }

  const query = search.toString()
  return query ? `${path}?${query}` : path
}

function serviceListPath(path: string, filters: ServiceListFilters = {}) {
  return withQuery(path, {
    status: filters.status,
    category_id: filters.categoryId,
    division: filters.division,
    owner_role_id: filters.ownerRoleId,
    client_visibility: filters.clientVisibility,
    branch_id: filters.branchId,
    search: filters.search,
    limit: filters.limit,
    offset: filters.offset,
  })
}

export const serviceAdministrationBackendApi = {
  listRoles(limit = 100, offset = 0, search?: string) {
    return apiClient.get<LimitOffsetPageDto<RoleDto>>(
      withQuery('/roles', { limit, offset, search }),
    )
  },

  listBranches(limit = 100, offset = 0) {
    return apiClient.get<LimitOffsetPageDto<BranchDto>>(
      withQuery('/branch/branches', { is_active: true, limit, offset }),
    )
  },

  listCategories(limit = 100, offset = 0) {
    return apiClient.get<LimitOffsetPageDto<ServiceCategoryDto>>(
      withQuery('/categories', { limit, offset }),
    )
  },

  listFieldTypes() {
    return apiClient.get<FieldTypeDto[]>(`${basePath}/request-field-types`)
  },

  listCatalogue(filters: ServiceListFilters = {}) {
    return apiClient.get<LimitOffsetPageDto<ServiceCatalogueCardDto>>(
      serviceListPath(`${basePath}/catalogue`, filters),
    )
  },

  getCatalogueDetail(serviceId: number) {
    return apiClient.get<ServiceCatalogueDetailDto>(`${basePath}/catalogue/${serviceId}`)
  },

  listServices(filters: ServiceListFilters = {}) {
    return apiClient.get<LimitOffsetPageDto<ServiceCoreDto>>(serviceListPath(basePath, filters))
  },

  getService(serviceId: number) {
    return apiClient.get<ServiceCoreDto>(`${basePath}/${serviceId}`)
  },

  createService(input: ServiceCreateDto) {
    return apiClient.post<ServiceCoreDto>(basePath, input)
  },

  updateService(serviceId: number, input: ServiceUpdateDto) {
    return apiClient.put<ServiceCoreDto>(`${basePath}/${serviceId}`, input)
  },

  deleteService(serviceId: number) {
    return apiClient.delete<MessageDto>(`${basePath}/${serviceId}`)
  },

  publishService(serviceId: number, input: ServicePublishDto) {
    return apiClient.post<ServiceCatalogueDetailDto>(`${basePath}/${serviceId}/publish`, input)
  },

  listSubservices(serviceId: number) {
    return apiClient.get<ServiceSubserviceDto[]>(`${basePath}/${serviceId}/subservices`)
  },

  replaceSubservices(serviceId: number, subservices: ServiceSubserviceInputDto[]) {
    return apiClient.put<ServiceSubserviceDto[]>(`${basePath}/${serviceId}/subservices`, {
      subservices,
    })
  },

  createSubservice(serviceId: number, input: ServiceSubserviceInputDto) {
    return apiClient.post<ServiceSubserviceDto>(`${basePath}/${serviceId}/subservices`, input)
  },

  updateSubservice(serviceId: number, subserviceId: number, input: ServiceSubserviceUpdateDto) {
    return apiClient.put<ServiceSubserviceDto>(
      `${basePath}/${serviceId}/subservices/${subserviceId}`,
      input,
    )
  },

  deleteSubservice(serviceId: number, subserviceId: number) {
    return apiClient.delete<MessageDto>(`${basePath}/${serviceId}/subservices/${subserviceId}`)
  },

  listRequestForms(serviceId: number) {
    return apiClient.get<RequestFormDto[]>(`${basePath}/${serviceId}/request-forms`)
  },

  createRequestForm(serviceId: number, input: RequestFormInputDto) {
    return apiClient.post<RequestFormDto>(`${basePath}/${serviceId}/request-forms`, input)
  },

  getRequestForm(serviceId: number, formId: number) {
    return apiClient.get<RequestFormDto>(`${basePath}/${serviceId}/request-forms/${formId}`)
  },

  updateRequestForm(serviceId: number, formId: number, input: RequestFormUpdateDto) {
    return apiClient.put<RequestFormDto>(`${basePath}/${serviceId}/request-forms/${formId}`, input)
  },

  deleteRequestForm(serviceId: number, formId: number) {
    return apiClient.delete<MessageDto>(`${basePath}/${serviceId}/request-forms/${formId}`)
  },

  activateRequestForm(serviceId: number, formId: number) {
    return apiClient.post<RequestFormDto>(
      `${basePath}/${serviceId}/request-forms/${formId}/activate`,
      {},
    )
  },

  listPricingConfigs(filters: PricingConfigListFilters = {}) {
    return apiClient.get<LimitOffsetPageDto<PricingConfigDto>>(
      withQuery(`${basePath}/pricing-configs`, {
        service_id: filters.serviceId,
        status: filters.status,
        pricing_type: filters.pricingType,
        search: filters.search,
        limit: filters.limit,
        offset: filters.offset,
      }),
    )
  },

  createPricingConfig(serviceId: number, input: PricingConfigInputDto) {
    return apiClient.post<PricingConfigDto>(`${basePath}/${serviceId}/pricing-configs`, input)
  },

  getPricingConfig(serviceId: number, configId: number) {
    return apiClient.get<PricingConfigDto>(`${basePath}/${serviceId}/pricing-configs/${configId}`)
  },

  updatePricingConfig(serviceId: number, configId: number, input: PricingConfigUpdateDto) {
    return apiClient.put<PricingConfigDto>(
      `${basePath}/${serviceId}/pricing-configs/${configId}`,
      input,
    )
  },

  deletePricingConfig(serviceId: number, configId: number) {
    return apiClient.delete<MessageDto>(`${basePath}/${serviceId}/pricing-configs/${configId}`)
  },

  activatePricingConfig(serviceId: number, configId: number) {
    return apiClient.post<PricingConfigDto>(
      `${basePath}/${serviceId}/pricing-configs/${configId}/activate`,
      {},
    )
  },

  listWorkflows(serviceId: number) {
    return apiClient.get<WorkflowDto[]>(`${basePath}/${serviceId}/workflows`)
  },

  createWorkflow(serviceId: number, input: WorkflowInputDto) {
    return apiClient.post<WorkflowDto>(`${basePath}/${serviceId}/workflows`, input)
  },

  getWorkflow(serviceId: number, workflowId: number) {
    return apiClient.get<WorkflowDto>(`${basePath}/${serviceId}/workflows/${workflowId}`)
  },

  updateWorkflow(serviceId: number, workflowId: number, input: WorkflowUpdateDto) {
    return apiClient.put<WorkflowDto>(`${basePath}/${serviceId}/workflows/${workflowId}`, input)
  },

  deleteWorkflow(serviceId: number, workflowId: number) {
    return apiClient.delete<MessageDto>(`${basePath}/${serviceId}/workflows/${workflowId}`)
  },

  activateWorkflow(serviceId: number, workflowId: number) {
    return apiClient.post<WorkflowDto>(
      `${basePath}/${serviceId}/workflows/${workflowId}/activate`,
      {},
    )
  },

  listWorkflowStages(serviceId: number, workflowId: number) {
    return apiClient.get<WorkflowStageDto[]>(
      `${basePath}/${serviceId}/workflows/${workflowId}/stages`,
    )
  },

  replaceWorkflowStages(serviceId: number, workflowId: number, stages: WorkflowStageInputDto[]) {
    return apiClient.put<WorkflowStageDto[]>(
      `${basePath}/${serviceId}/workflows/${workflowId}/stages`,
      { stages },
    )
  },

  createWorkflowStage(serviceId: number, workflowId: number, input: WorkflowStageInputDto) {
    return apiClient.post<WorkflowStageDto>(
      `${basePath}/${serviceId}/workflows/${workflowId}/stages`,
      input,
    )
  },

  updateWorkflowStage(
    serviceId: number,
    workflowId: number,
    stageId: number,
    input: WorkflowStageUpdateDto,
  ) {
    return apiClient.put<WorkflowStageDto>(
      `${basePath}/${serviceId}/workflows/${workflowId}/stages/${stageId}`,
      input,
    )
  },

  deleteWorkflowStage(serviceId: number, workflowId: number, stageId: number) {
    return apiClient.delete<MessageDto>(
      `${basePath}/${serviceId}/workflows/${workflowId}/stages/${stageId}`,
    )
  },

  seedWorkflow(serviceId: number, input: WorkflowSeedInputDto) {
    return apiClient.post<WorkflowDto>(`${basePath}/${serviceId}/workflow-seed`, input)
  },

  getWorkflowSummary(serviceId: number) {
    return apiClient.get<Record<string, unknown>>(`${basePath}/${serviceId}/workflow-summary`)
  },

  listBranchActivations(serviceId: number) {
    return apiClient.get<BranchActivationDto[]>(`${basePath}/${serviceId}/branch-activations`)
  },

  upsertBranchActivations(serviceId: number, branchActivations: BranchActivationInputDto[]) {
    return apiClient.put<BranchActivationDto[]>(`${basePath}/${serviceId}/branch-activations`, {
      branch_activations: branchActivations,
    })
  },

  getBranchActivationMatrix(filters: BranchActivationMatrixFilters = {}) {
    return apiClient.get<ServiceCatalogueCardDto[]>(
      withQuery(`${basePath}/branch-activation-matrix`, {
        division: filters.division,
        status: filters.status,
        branch_id: filters.branchId,
        search: filters.search,
      }),
    )
  },
}

export const serviceAdministrationBackendPaths = {
  basePath,
  withQuery,
  serviceListPath,
}
