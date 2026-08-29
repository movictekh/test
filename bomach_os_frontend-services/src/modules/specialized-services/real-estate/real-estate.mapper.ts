import type {
  BrokerageListing,
  BrokerageStats,
  Estate,
  EstateChoices,
  EstateDocument,
  EstatePlotLayoutItem,
  EstateStats,
  PaginatedBrokerageListings,
  PaginatedEstates,
  PaginatedProperties,
  Property,
} from './real-estate.types'

type Row = Record<string, unknown>
const row = (v: unknown): Row =>
  typeof v === 'object' && v !== null && !Array.isArray(v) ? (v as Row) : {}
const str = (v: unknown, f = '') => (typeof v === 'string' ? v : f)
const num = (v: unknown, f = 0) => {
  const n = Number(v)
  return Number.isFinite(n) ? n : f
}
const nnum = (v: unknown) => (v == null || v === '' ? null : num(v))
const bool = (v: unknown) => v === true
const strings = (v: unknown) =>
  Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : []
const paginatedItems = (payload: unknown) => {
  if (Array.isArray(payload)) return { count: payload.length, items: payload }
  const v = row(payload)
  const items = Array.isArray(v.items) ? v.items : Array.isArray(v.results) ? v.results : []
  return { count: num(v.count, items.length), items }
}

function mapDocument(payload: unknown): EstateDocument {
  const v = row(payload)
  return { id: num(v.id), file: str(v.file), caption: str(v.caption), createdAt: str(v.created_at) }
}

export function mapEstate(payload: unknown): Estate {
  const v = row(payload)
  return {
    id: num(v.id),
    isOurEstate: bool(v.is_our_estate),
    legalFee: nnum(v.legal_fee),
    developmentFee: nnum(v.development_fee),
    receiptFee: nnum(v.receipt_fee),
    estateName: str(v.estate_name),
    estateCode: str(v.estate_code),
    estateType: str(v.estate_type, 'land') as Estate['estateType'],
    estateTypeDisplay: str(v.estate_type_display),
    developerCompanyName: str(v.developer_company_name),
    estateDescription: str(v.estate_description),
    country: str(v.country),
    countryCode: str(v.country_code),
    state: str(v.state),
    cityTown: str(v.city_town),
    preciseAddress: str(v.precise_address),
    boundary: Array.isArray(v.boundary)
      ? v.boundary.map((x) => row(x)).map((x) => ({ lat: num(x.lat), lng: num(x.lng) }))
      : [],
    documents: Array.isArray(v.documents) ? v.documents.map(mapDocument) : [],
    hasCOfO: bool(v.has_c_of_o),
    hasDeedOfAssignment: bool(v.has_deed_of_assignment),
    hasSurveyPlan: bool(v.has_survey_plan),
    zoningInformation: str(v.zoning_information),
    titleDocuments: strings(v.title_documents),
    hasPlanningPermit: bool(v.has_planning_permit),
    hasBuildingApproval: bool(v.has_building_approval),
    hasEnvironmentalClearance: bool(v.has_environmental_clearance),
    governmentApprovals: strings(v.government_approvals),
    pricePerSqm: num(v.price_per_sqm),
    availablePlotSizes: str(v.available_plot_sizes),
    minPriceOtherProperties: nnum(v.min_price_other_properties),
    maxPriceOtherProperties: nnum(v.max_price_other_properties),
    estateStatus: str(v.estate_status, 'available') as Estate['estateStatus'],
    estateStatusDisplay: str(v.estate_status_display),
    totalArea: nnum(v.total_area),
    areaUnit: str(v.area_unit, 'sqm'),
    hasRoads: bool(v.has_roads),
    hasElectricity: bool(v.has_electricity),
    hasWater: bool(v.has_water),
    hasFencing: bool(v.has_fencing),
    hasSecurity: bool(v.has_security),
    hasDrainage: bool(v.has_drainage),
    hasRecreation: bool(v.has_recreation),
    amenities: strings(v.amenities),
    tags: strings(v.tags),
    isActive: bool(v.is_active),
    createdAt: str(v.created_at),
    updatedAt: str(v.updated_at),
  }
}

export function mapEstateList(payload: unknown): PaginatedEstates {
  const p = paginatedItems(payload)
  return { count: p.count, items: p.items.map(mapEstate) }
}

export function mapEstateStats(payload: unknown): EstateStats {
  const v = row(payload)
  return {
    total: num(v.total),
    sold: num(v.sold),
    reserved: num(v.reserved),
    available: num(v.available),
    hold: num(v.hold),
    notForSale: num(v.not_for_sale),
    totalValue: num(v.total_value),
    soldValue: num(v.sold_value),
  }
}

export function mapPlotLayoutItem(payload: unknown): EstatePlotLayoutItem {
  const v = row(payload)
  return {
    id: num(v.id),
    plotNumber: nnum(v.plot_number),
    propertyName: str(v.property_name),
    status: str(v.status, 'available') as EstatePlotLayoutItem['status'],
    statusDisplay: str(v.status_display),
    plotSize: nnum(v.plot_size),
    price: num(v.price),
    clientName: str(v.client_name),
  }
}

export const mapEstateLayout = (payload: unknown) =>
  Array.isArray(payload) ? payload.map(mapPlotLayoutItem) : []

export function mapEstateChoices(payload: unknown): EstateChoices {
  const v = row(payload)
  const choices = (value: unknown) =>
    Array.isArray(value)
      ? value.map((x) => row(x)).map((x) => ({ value: str(x.value), label: str(x.label) }))
      : []
  return {
    estateType: choices(v.estate_type) as EstateChoices['estateType'],
    estateStatus: choices(v.estate_status) as EstateChoices['estateStatus'],
    areaUnit: choices(v.area_unit),
  }
}

function mapImage(payload: unknown) {
  const v = row(payload)
  return {
    id: num(v.id),
    image: str(v.image),
    caption: str(v.caption),
    createdAt: str(v.created_at),
  }
}

export function mapProperty(payload: unknown): Property {
  const v = row(payload)
  return {
    id: num(v.id),
    isOurProperty: bool(v.is_our_property),
    estateId: nnum(v.estate_id),
    estateName: str(v.estate_name),
    estateCode: str(v.estate_code),
    propertyType: str(v.property_type, 'plot') as Property['propertyType'],
    propertyTypeDisplay: str(v.property_type_display),
    propertyName: str(v.property_name),
    price: num(v.price),
    description: str(v.description),
    status: str(v.status, 'available') as Property['status'],
    statusDisplay: str(v.status_display),
    plotNumber: nnum(v.plot_number),
    clientName: str(v.client_name),
    plotSize: nnum(v.plot_size),
    plotSizeUnit: str(v.plot_size_unit),
    buildingTypeResidential: str(v.building_type_residential),
    buildingTypeResidentialDisplay: str(v.building_type_residential_display),
    bedrooms: nnum(v.bedrooms),
    bathrooms: nnum(v.bathrooms),
    floorsResidential: nnum(v.floors_residential),
    totalAreaResidential: nnum(v.total_area_residential),
    buildingTypeCommercial: str(v.building_type_commercial),
    buildingTypeCommercialDisplay: str(v.building_type_commercial_display),
    totalAreaCommercial: nnum(v.total_area_commercial),
    numberOfFloors: nnum(v.number_of_floors),
    unitsOffices: nnum(v.units_offices),
    images: Array.isArray(v.images) ? v.images.map(mapImage) : [],
    isActive: bool(v.is_active),
    createdAt: str(v.created_at),
    updatedAt: str(v.updated_at),
  }
}

export function mapPropertyList(payload: unknown): PaginatedProperties {
  const p = paginatedItems(payload)
  return { count: p.count, items: p.items.map(mapProperty) }
}

function mapBrokerageImage(payload: unknown) {
  const v = row(payload)
  return {
    id: num(v.id),
    image: str(v.image),
    caption: str(v.caption),
    createdAt: str(v.created_at),
  }
}

export function mapBrokerageListing(payload: unknown): BrokerageListing {
  const v = row(payload)
  return {
    id: num(v.id),
    title: str(v.title),
    description: str(v.description),
    location: str(v.location),
    price: num(v.price),
    propertyType: str(v.property_type, 'land') as BrokerageListing['propertyType'],
    ownerName: str(v.owner_name),
    ownerPhone: str(v.owner_phone),
    ownerEmail: str(v.owner_email),
    commissionRate: num(v.commission_rate),
    verificationStatus: str(
      v.verification_status,
      'pending',
    ) as BrokerageListing['verificationStatus'],
    status: str(v.status, 'available') as BrokerageListing['status'],
    assignedAgentId: nnum(v.assigned_agent_id),
    estateId: nnum(v.estate_id),
    tags: strings(v.tags),
    isActive: bool(v.is_active),
    images: Array.isArray(v.images) ? v.images.map(mapBrokerageImage) : [],
    createdAt: str(v.created_at),
    updatedAt: str(v.updated_at),
  }
}

export function mapBrokerageList(payload: unknown): PaginatedBrokerageListings {
  const p = paginatedItems(payload)
  return { count: p.count, items: p.items.map(mapBrokerageListing) }
}

export function mapBrokerageStats(payload: unknown): BrokerageStats {
  const v = row(payload)
  return {
    total: num(v.total),
    verified: num(v.verified),
    pendingVerification: num(v.pending_verification),
    inspectionDue: num(v.inspection_due),
    sold: num(v.sold),
    available: num(v.available),
    offMarket: num(v.off_market),
    totalListingValue: num(v.total_listing_value),
  }
}
