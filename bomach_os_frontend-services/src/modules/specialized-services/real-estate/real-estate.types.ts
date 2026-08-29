export type EstateType = 'residential' | 'commercial' | 'industrial' | 'mixed_use' | 'land'
export type EstateStatus = 'available' | 'sold_out' | 'under_development' | 'coming_soon'
export type PropertyType = 'plot' | 'residential' | 'commercial'
export type PropertyStatus = 'not-for-sale' | 'available' | 'reserved' | 'sold' | 'hold'
export type BrokerageVerificationStatus = 'pending' | 'verified' | 'inspection_due'
export type BrokerageStatus = 'available' | 'sold' | 'off_market'
export type BrokeragePropertyType = 'residential' | 'commercial' | 'land'

export interface Choice<Value extends string = string> {
  value: Value
  label: string
}

export interface EstateDocument {
  id: number
  file: string
  caption: string
  createdAt: string
}

export interface Estate {
  id: number
  isOurEstate: boolean
  legalFee: number | null
  developmentFee: number | null
  receiptFee: number | null
  estateName: string
  estateCode: string
  estateType: EstateType
  estateTypeDisplay: string
  developerCompanyName: string
  estateDescription: string
  country: string
  countryCode: string
  state: string
  cityTown: string
  preciseAddress: string
  boundary: Array<{ lat: number; lng: number }>
  documents: EstateDocument[]
  hasCOfO: boolean
  hasDeedOfAssignment: boolean
  hasSurveyPlan: boolean
  zoningInformation: string
  titleDocuments: string[]
  hasPlanningPermit: boolean
  hasBuildingApproval: boolean
  hasEnvironmentalClearance: boolean
  governmentApprovals: string[]
  pricePerSqm: number
  availablePlotSizes: string
  minPriceOtherProperties: number | null
  maxPriceOtherProperties: number | null
  estateStatus: EstateStatus
  estateStatusDisplay: string
  totalArea: number | null
  areaUnit: string
  hasRoads: boolean
  hasElectricity: boolean
  hasWater: boolean
  hasFencing: boolean
  hasSecurity: boolean
  hasDrainage: boolean
  hasRecreation: boolean
  amenities: string[]
  tags: string[]
  isActive: boolean
  createdAt: string
  updatedAt: string
}

export interface EstateFilters {
  search?: string
  estateType?: EstateType
  estateStatus?: EstateStatus
  country?: string
  isOurEstate?: boolean
  isActive?: boolean
  page?: number
  limit?: number
}

export interface PaginatedEstates {
  count: number
  items: Estate[]
}

export interface EstateStats {
  total: number
  sold: number
  reserved: number
  available: number
  hold: number
  notForSale: number
  totalValue: number
  soldValue: number
}

export interface EstatePlotLayoutItem {
  id: number
  plotNumber: number | null
  propertyName: string
  status: PropertyStatus
  statusDisplay: string
  plotSize: number | null
  price: number
  clientName: string
}

export interface EstateChoices {
  estateType: Choice<EstateType>[]
  estateStatus: Choice<EstateStatus>[]
  areaUnit: Choice[]
}

export interface CreateEstateInput {
  isOurEstate: boolean
  estateName: string
  estateCode: string
  estateType: EstateType
  developerCompanyName: string
  estateDescription: string
  country: string
  countryCode?: string
  state: string
  cityTown: string
  preciseAddress: string
  hasCOfO: boolean
  hasDeedOfAssignment: boolean
  hasSurveyPlan: boolean
  zoningInformation?: string
  hasPlanningPermit: boolean
  hasBuildingApproval: boolean
  hasEnvironmentalClearance: boolean
  pricePerSqm: number
  availablePlotSizes?: string
  minPriceOtherProperties?: number | null
  maxPriceOtherProperties?: number | null
  estateStatus: EstateStatus
  totalArea?: number | null
  areaUnit: string
  hasRoads: boolean
  hasElectricity: boolean
  hasWater: boolean
  hasFencing: boolean
  hasSecurity: boolean
  hasDrainage: boolean
  hasRecreation: boolean
  legalFee?: number | null
  developmentFee?: number | null
  receiptFee?: number | null
  tags?: string[]
  documents?: string[]
}

export interface PropertyImage {
  id: number
  image: string
  caption: string
  createdAt: string
}

export interface Property {
  id: number
  isOurProperty: boolean
  estateId: number | null
  estateName: string
  estateCode: string
  propertyType: PropertyType
  propertyTypeDisplay: string
  propertyName: string
  price: number
  description: string
  status: PropertyStatus
  statusDisplay: string
  plotNumber: number | null
  clientName: string
  plotSize: number | null
  plotSizeUnit: string
  buildingTypeResidential: string
  buildingTypeResidentialDisplay: string
  bedrooms: number | null
  bathrooms: number | null
  floorsResidential: number | null
  totalAreaResidential: number | null
  buildingTypeCommercial: string
  buildingTypeCommercialDisplay: string
  totalAreaCommercial: number | null
  numberOfFloors: number | null
  unitsOffices: number | null
  images: PropertyImage[]
  isActive: boolean
  createdAt: string
  updatedAt: string
}

export interface PropertyFilters {
  propertyType?: PropertyType
  status?: PropertyStatus
  isActive?: boolean
  search?: string
  page?: number
  limit?: number
}

export interface PaginatedProperties {
  count: number
  items: Property[]
}

export interface CreatePropertyInput {
  isOurProperty: boolean
  propertyType: PropertyType
  propertyName: string
  price: number
  description?: string
  status: PropertyStatus
  plotNumber?: number | null
  clientName?: string
  plotSize?: number | null
  plotSizeUnit?: string
  buildingTypeResidential?: string
  bedrooms?: number | null
  bathrooms?: number | null
  floorsResidential?: number | null
  totalAreaResidential?: number | null
  buildingTypeCommercial?: string
  totalAreaCommercial?: number | null
  numberOfFloors?: number | null
  unitsOffices?: number | null
  images?: string[]
}

export interface QuickUpdatePlotInput {
  status?: PropertyStatus
  price?: number
  clientName?: string
}

export type BatchItemStatus = 'queued' | 'creating' | 'created' | 'failed'

export interface PropertyBatchItem {
  key: string
  sequence: number
  input: CreatePropertyInput
  status: BatchItemStatus
  propertyId: number | null
  error: string
}

export interface BrokerageListing {
  id: number
  title: string
  description: string
  location: string
  price: number
  propertyType: BrokeragePropertyType
  ownerName: string
  ownerPhone: string
  ownerEmail: string
  commissionRate: number
  verificationStatus: BrokerageVerificationStatus
  status: BrokerageStatus
  assignedAgentId: number | null
  estateId: number | null
  tags: string[]
  isActive: boolean
  images: Array<{ id: number; image: string; caption: string; createdAt: string }>
  createdAt: string
  updatedAt: string
}

export interface BrokerageFilters {
  search?: string
  status?: BrokerageStatus
  verificationStatus?: BrokerageVerificationStatus
  propertyType?: BrokeragePropertyType
  isActive?: boolean
  page?: number
  limit?: number
}

export interface PaginatedBrokerageListings {
  count: number
  items: BrokerageListing[]
}

export interface BrokerageStats {
  total: number
  verified: number
  pendingVerification: number
  inspectionDue: number
  sold: number
  available: number
  offMarket: number
  totalListingValue: number
}

export interface CreateBrokerageInput {
  title: string
  description?: string
  location: string
  price: number
  propertyType: BrokeragePropertyType
  ownerName: string
  ownerPhone?: string
  ownerEmail?: string
  commissionRate: number
  verificationStatus: BrokerageVerificationStatus
  status: BrokerageStatus
  assignedAgentId?: number | null
  estateId?: number | null
  tags?: string[]
  isActive?: boolean
  images?: string[]
}

export const propertyStatuses: Array<Choice<PropertyStatus>> = [
  { value: 'available', label: 'Available' },
  { value: 'reserved', label: 'Reserved' },
  { value: 'sold', label: 'Sold' },
  { value: 'hold', label: 'Hold' },
  { value: 'not-for-sale', label: 'Not for Sale' },
]

export const propertyTypes: Array<Choice<PropertyType>> = [
  { value: 'plot', label: 'Plot of Land' },
  { value: 'residential', label: 'Residential Building' },
  { value: 'commercial', label: 'Commercial Building' },
]

export const estateTypes: Array<Choice<EstateType>> = [
  { value: 'residential', label: 'Residential' },
  { value: 'commercial', label: 'Commercial' },
  { value: 'industrial', label: 'Industrial' },
  { value: 'mixed_use', label: 'Mixed Use' },
  { value: 'land', label: 'Land' },
]

export const estateStatuses: Array<Choice<EstateStatus>> = [
  { value: 'available', label: 'Available' },
  { value: 'sold_out', label: 'Sold Out' },
  { value: 'under_development', label: 'Under Development' },
  { value: 'coming_soon', label: 'Coming Soon' },
]

export const brokerageVerificationStatuses: Array<Choice<BrokerageVerificationStatus>> = [
  { value: 'pending', label: 'Pending Verification' },
  { value: 'verified', label: 'Verified' },
  { value: 'inspection_due', label: 'Inspection Due' },
]

export const brokerageStatuses: Array<Choice<BrokerageStatus>> = [
  { value: 'available', label: 'Available' },
  { value: 'sold', label: 'Sold' },
  { value: 'off_market', label: 'Off Market' },
]
