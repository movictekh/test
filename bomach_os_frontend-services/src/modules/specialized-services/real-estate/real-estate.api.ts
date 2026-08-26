import { apiClient } from '@/shared/api/api-client'
import { compactBoundary } from './real-estate.boundary'
import {
  mapBrokerageList,
  mapBrokerageListing,
  mapBrokerageStats,
  mapEstate,
  mapEstateChoices,
  mapEstateLayout,
  mapEstateList,
  mapEstateStats,
  mapPlotLayoutItem,
  mapProperty,
  mapPropertyList,
} from './real-estate.mapper'
import type {
  BrokerageFilters,
  BrokerageVerificationStatus,
  CreateBrokerageInput,
  CreateEstateInput,
  CreatePropertyInput,
  EstateFilters,
  PropertyFilters,
  QuickUpdatePlotInput,
} from './real-estate.types'
import type { Estate } from './real-estate.types'

function pageQuery(filters: { page?: number; limit?: number }) {
  const q = new URLSearchParams()
  const limit = filters.limit ?? 20,
    page = filters.page ?? 1
  q.set('limit', String(limit))
  q.set('offset', String((page - 1) * limit))
  return q
}
function estateQuery(filters: EstateFilters = {}) {
  const q = pageQuery(filters)
  if (filters.search) q.set('search', filters.search)
  if (filters.estateType) q.set('estate_type', filters.estateType)
  if (filters.estateStatus) q.set('estate_status', filters.estateStatus)
  if (filters.country) q.set('country', filters.country)
  if (filters.isOurEstate !== undefined) q.set('is_our_estate', String(filters.isOurEstate))
  if (filters.isActive !== undefined) q.set('is_active', String(filters.isActive))
  return q.toString()
}
function propertyQuery(filters: PropertyFilters = {}) {
  const q = pageQuery(filters)
  if (filters.search) q.set('search', filters.search)
  if (filters.propertyType) q.set('property_type', filters.propertyType)
  if (filters.status) q.set('status', filters.status)
  if (filters.isActive !== undefined) q.set('is_active', String(filters.isActive))
  return q.toString()
}
function brokerageQuery(filters: BrokerageFilters = {}) {
  const q = pageQuery(filters)
  if (filters.search) q.set('search', filters.search)
  if (filters.status) q.set('status', filters.status)
  if (filters.verificationStatus) q.set('verification_status', filters.verificationStatus)
  if (filters.propertyType) q.set('property_type', filters.propertyType)
  if (filters.isActive !== undefined) q.set('is_active', String(filters.isActive))
  return q.toString()
}

const estatePayload = (i: CreateEstateInput) => ({
  is_our_estate: i.isOurEstate,
  estate_name: i.estateName,
  estate_code: i.estateCode,
  estate_type: i.estateType,
  developer_company_name: i.developerCompanyName,
  estate_description: i.estateDescription,
  country: i.country,
  country_code: i.countryCode ?? '',
  state: i.state,
  city_town: i.cityTown,
  precise_address: i.preciseAddress,
  boundary: compactBoundary(i.boundary),
  estate_map_url: i.estateMapUrl ?? '',
  virtual_tour_url: i.virtualTourUrl ?? '',
  documents: i.documents ?? [],
  has_c_of_o: i.hasCOfO,
  has_deed_of_assignment: i.hasDeedOfAssignment,
  has_survey_plan: i.hasSurveyPlan,
  zoning_information: i.zoningInformation ?? '',
  has_planning_permit: i.hasPlanningPermit,
  has_building_approval: i.hasBuildingApproval,
  has_environmental_clearance: i.hasEnvironmentalClearance,
  price_per_sqm: i.pricePerSqm,
  available_plot_sizes: i.availablePlotSizes ?? '',
  min_price_other_properties: i.minPriceOtherProperties ?? null,
  max_price_other_properties: i.maxPriceOtherProperties ?? null,
  estate_status: i.estateStatus,
  total_area: i.totalArea ?? null,
  area_unit: i.areaUnit,
  has_roads: i.hasRoads,
  has_electricity: i.hasElectricity,
  has_water: i.hasWater,
  has_fencing: i.hasFencing,
  has_security: i.hasSecurity,
  has_drainage: i.hasDrainage,
  has_recreation: i.hasRecreation,
  legal_fee: i.legalFee ?? null,
  development_fee: i.developmentFee ?? null,
  receipt_fee: i.receiptFee ?? null,
  reservation_allowed: i.reservationAllowed,
  reservation_threshold_percent: i.reservationAllowed
    ? (i.reservationThresholdPercent ?? null)
    : null,
  installment_allowed: i.installmentAllowed,
  max_installment_months: i.installmentAllowed ? (i.maxInstallmentMonths ?? null) : null,
  reservation_payment_window_hours: i.reservationPaymentWindowHours,
  tags: i.tags ?? [],
})
const propertyPayload = (i: CreatePropertyInput) => ({
  is_our_property: i.isOurProperty,
  property_type: i.propertyType,
  property_name: i.propertyName,
  ...(i.price != null ? { price: i.price } : {}),
  boundary: compactBoundary(i.boundary),
  description: i.description ?? '',
  status: i.status,
  plot_number: i.plotNumber ?? null,
  client_name: i.clientName ?? '',
  plot_size: i.plotSize ?? null,
  plot_size_unit: i.plotSizeUnit ?? 'sqm',
  building_type_residential: i.buildingTypeResidential ?? '',
  bedrooms: i.bedrooms ?? null,
  bathrooms: i.bathrooms ?? null,
  floors_residential: i.floorsResidential ?? null,
  total_area_residential: i.totalAreaResidential ?? null,
  building_type_commercial: i.buildingTypeCommercial ?? '',
  total_area_commercial: i.totalAreaCommercial ?? null,
  number_of_floors: i.numberOfFloors ?? null,
  units_offices: i.unitsOffices ?? null,
  images: i.images ?? [],
})
const propertyPatchPayload = (i: Partial<CreatePropertyInput>) => ({
  ...('isOurProperty' in i ? { is_our_property: i.isOurProperty } : {}),
  ...('propertyName' in i ? { property_name: i.propertyName } : {}),
  ...('price' in i ? { price: i.price } : {}),
  ...('boundary' in i ? { boundary: compactBoundary(i.boundary) } : {}),
  ...('description' in i ? { description: i.description } : {}),
  ...('status' in i ? { status: i.status } : {}),
  ...('plotNumber' in i ? { plot_number: i.plotNumber } : {}),
  ...('plotSize' in i ? { plot_size: i.plotSize } : {}),
  ...('plotSizeUnit' in i ? { plot_size_unit: i.plotSizeUnit } : {}),
  ...('buildingTypeResidential' in i
    ? { building_type_residential: i.buildingTypeResidential }
    : {}),
  ...('bedrooms' in i ? { bedrooms: i.bedrooms } : {}),
  ...('bathrooms' in i ? { bathrooms: i.bathrooms } : {}),
  ...('floorsResidential' in i ? { floors_residential: i.floorsResidential } : {}),
  ...('totalAreaResidential' in i ? { total_area_residential: i.totalAreaResidential } : {}),
  ...('buildingTypeCommercial' in i ? { building_type_commercial: i.buildingTypeCommercial } : {}),
  ...('totalAreaCommercial' in i ? { total_area_commercial: i.totalAreaCommercial } : {}),
  ...('numberOfFloors' in i ? { number_of_floors: i.numberOfFloors } : {}),
  ...('unitsOffices' in i ? { units_offices: i.unitsOffices } : {}),
})
const brokeragePayload = (i: CreateBrokerageInput) => ({
  title: i.title,
  description: i.description ?? '',
  location: i.location,
  boundary: compactBoundary(i.boundary),
  price: i.price,
  property_type: i.propertyType,
  owner_name: i.ownerName,
  owner_phone: i.ownerPhone ?? '',
  owner_email: i.ownerEmail ?? '',
  commission_rate: i.commissionRate,
  verification_status: i.verificationStatus,
  status: i.status,
  assigned_agent_id: i.assignedAgentId ?? null,
  estate_id: i.estateId ?? null,
  tags: i.tags ?? [],
  is_active: i.isActive ?? true,
  images: i.images ?? [],
})

export const realEstateApi = {
  uploadEstateAsset: async (file: File, signal?: AbortSignal): Promise<string> => {
    const formData = new FormData()
    formData.set('file', file)
    const payload = await apiClient.post<{ url: string }>('/others/upload-file', formData, {
      ...(signal ? { signal } : {}),
    })
    return payload.url
  },
  listEstates: async (f: EstateFilters = {}) =>
    mapEstateList(await apiClient.get<unknown>(`/estates/?${estateQuery(f)}`)),
  estateDetail: async (id: number) => mapEstate(await apiClient.get<unknown>(`/estates/${id}`)),
  estateStats: async (id: number) =>
    mapEstateStats(await apiClient.get<unknown>(`/estates/${id}/stats`)),
  estateLayout: async (id: number) =>
    mapEstateLayout(await apiClient.get<unknown>(`/estates/${id}/layout`)),
  estateChoices: async () =>
    mapEstateChoices(await apiClient.get<unknown>('/estates/choices/fields')),
  createEstate: async (i: CreateEstateInput) =>
    mapEstate(await apiClient.post<unknown>('/estates/', estatePayload(i))),
  updateEstate: async (id: number, i: CreateEstateInput) =>
    mapEstate(await apiClient.put<unknown>(`/estates/${id}`, estatePayload(i))),
  deleteEstate: async (id: number) => apiClient.delete<unknown>(`/estates/${id}`),

  listProperties: async (estateId: number, f: PropertyFilters = {}) =>
    mapPropertyList(
      await apiClient.get<unknown>(`/estates/${estateId}/properties?${propertyQuery(f)}`),
    ),
  listAllProperties: async (estateId: number) => {
    const limit = 250
    const properties = []
    let page = 1
    let count = Number.POSITIVE_INFINITY

    while (properties.length < count) {
      const result = mapPropertyList(
        await apiClient.get<unknown>(
          `/estates/${estateId}/properties?${propertyQuery({ page, limit })}`,
        ),
      )
      count = result.count
      properties.push(...result.items)
      if (!result.items.length) break
      page += 1
    }

    return properties
  },
  listStandaloneProperties: async (f: PropertyFilters = {}) =>
    mapPropertyList(await apiClient.get<unknown>(`/estates/properties/all?${propertyQuery(f)}`)),
  propertyDetail: async (estateId: number, id: number) =>
    mapProperty(await apiClient.get<unknown>(`/estates/${estateId}/properties/${id}`)),
  createProperty: async (estateId: number, i: CreatePropertyInput) =>
    mapProperty(
      await apiClient.post<unknown>(`/estates/${estateId}/properties`, propertyPayload(i)),
    ),
  createStandaloneProperty: async (i: CreatePropertyInput) =>
    mapProperty(await apiClient.post<unknown>('/estates/properties/all', propertyPayload(i))),
  updateProperty: async (estateId: number, id: number, i: CreatePropertyInput) =>
    mapProperty(
      await apiClient.put<unknown>(`/estates/${estateId}/properties/${id}`, propertyPayload(i)),
    ),
  updatePropertyFields: async (estateId: number, id: number, i: Partial<CreatePropertyInput>) =>
    mapProperty(
      await apiClient.put<unknown>(
        `/estates/${estateId}/properties/${id}`,
        propertyPatchPayload(i),
      ),
    ),
  deleteProperty: async (estateId: number, id: number) =>
    apiClient.delete<unknown>(`/estates/${estateId}/properties/${id}`),
  quickUpdatePropertyInventory: async (estateId: number, id: number, i: QuickUpdatePlotInput) =>
    mapPlotLayoutItem(
      await apiClient.patch<unknown>(`/estates/${estateId}/plots/${id}/quick-update`, {
        ...(i.status !== undefined ? { status: i.status } : {}),
        ...(i.price !== undefined ? { price: i.price } : {}),
        ...(i.clientName !== undefined ? { client_name: i.clientName } : {}),
      }),
    ),

  listBrokerage: async (f: BrokerageFilters = {}) =>
    mapBrokerageList(await apiClient.get<unknown>(`/brokerage/?${brokerageQuery(f)}`)),
  brokerageStats: async () => mapBrokerageStats(await apiClient.get<unknown>('/brokerage/stats')),
  createBrokerage: async (i: CreateBrokerageInput) =>
    mapBrokerageListing(await apiClient.post<unknown>('/brokerage/', brokeragePayload(i))),
  updateBrokerage: async (id: number, i: CreateBrokerageInput) =>
    mapBrokerageListing(await apiClient.put<unknown>(`/brokerage/${id}`, brokeragePayload(i))),
  verifyBrokerage: async (id: number, verificationStatus: BrokerageVerificationStatus) =>
    mapBrokerageListing(
      await apiClient.patch<unknown>(`/brokerage/${id}/verify`, {
        verification_status: verificationStatus,
      }),
    ),
  deleteBrokerage: async (id: number) => apiClient.delete<unknown>(`/brokerage/${id}`),
}

export function mapEstateToInput(estate: Estate): CreateEstateInput {
  return {
    isOurEstate: estate.isOurEstate,
    estateName: estate.estateName,
    estateCode: estate.estateCode,
    estateType: estate.estateType,
    developerCompanyName: estate.developerCompanyName,
    estateDescription: estate.estateDescription,
    country: estate.country,
    countryCode: estate.countryCode,
    state: estate.state,
    cityTown: estate.cityTown,
    preciseAddress: estate.preciseAddress,
    boundary: estate.boundary,
    estateMapUrl: estate.estateMapUrl,
    virtualTourUrl: estate.virtualTourUrl,
    hasCOfO: estate.hasCOfO,
    hasDeedOfAssignment: estate.hasDeedOfAssignment,
    hasSurveyPlan: estate.hasSurveyPlan,
    zoningInformation: estate.zoningInformation,
    hasPlanningPermit: estate.hasPlanningPermit,
    hasBuildingApproval: estate.hasBuildingApproval,
    hasEnvironmentalClearance: estate.hasEnvironmentalClearance,
    pricePerSqm: estate.pricePerSqm,
    availablePlotSizes: estate.availablePlotSizes,
    minPriceOtherProperties: estate.minPriceOtherProperties,
    maxPriceOtherProperties: estate.maxPriceOtherProperties,
    estateStatus: estate.estateStatus,
    totalArea: estate.totalArea,
    areaUnit: estate.areaUnit,
    hasRoads: estate.hasRoads,
    hasElectricity: estate.hasElectricity,
    hasWater: estate.hasWater,
    hasFencing: estate.hasFencing,
    hasSecurity: estate.hasSecurity,
    hasDrainage: estate.hasDrainage,
    hasRecreation: estate.hasRecreation,
    legalFee: estate.legalFee,
    developmentFee: estate.developmentFee,
    receiptFee: estate.receiptFee,
    reservationAllowed: estate.reservationAllowed,
    reservationThresholdPercent: estate.reservationThresholdPercent,
    installmentAllowed: estate.installmentAllowed,
    maxInstallmentMonths: estate.maxInstallmentMonths,
    reservationPaymentWindowHours: estate.reservationPaymentWindowHours,
    tags: estate.tags,
    documents: estate.documents.map((document) => document.file),
  }
}
