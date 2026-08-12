import type {
  CreateBrokerageInput,
  CreateEstateInput,
  CreatePropertyInput,
  QuickUpdatePlotInput,
} from './real-estate.types'
export function validateQuickPlotUpdate(i: QuickUpdatePlotInput) {
  if (i.price !== undefined && (!Number.isFinite(i.price) || i.price <= 0))
    return 'Plot price must be greater than zero.'
  if ((i.status === 'reserved' || i.status === 'sold') && !i.clientName?.trim())
    return i.status === 'reserved'
      ? 'A reservation holder is required when reserving a plot.'
      : 'A client name is required when marking a plot as sold.'
  return ''
}
export function validateEstate(i: CreateEstateInput) {
  if (!i.estateName.trim()) return 'Estate name is required.'
  if (!i.estateCode.trim()) return 'Estate code is required.'
  if (!i.developerCompanyName.trim()) return 'Developer / company name is required.'
  if (!i.estateDescription.trim()) return 'Estate description is required.'
  if (!i.country.trim() || !i.state.trim() || !i.cityTown.trim() || !i.preciseAddress.trim())
    return 'Complete Estate location is required.'
  if (!Number.isFinite(i.pricePerSqm) || i.pricePerSqm < 0)
    return 'Price per square metre must be zero or greater.'
  if (
    i.minPriceOtherProperties != null &&
    i.maxPriceOtherProperties != null &&
    i.minPriceOtherProperties > i.maxPriceOtherProperties
  )
    return 'Minimum property price cannot exceed maximum property price.'
  return ''
}
export function validateProperty(i: CreatePropertyInput) {
  if (!i.propertyName.trim()) return 'Property name is required.'
  if (!Number.isFinite(i.price) || i.price <= 0) return 'Property price must be greater than zero.'
  if (i.propertyType === 'plot' && (!i.plotSize || i.plotSize <= 0))
    return 'Plot size must be greater than zero.'
  if (i.propertyType === 'residential') {
    if (!i.buildingTypeResidential) return 'Residential building type is required.'
    if (!i.bedrooms || !i.bathrooms || !i.totalAreaResidential)
      return 'Bedrooms, bathrooms and total area are required for residential property.'
  }
  if (i.propertyType === 'commercial') {
    if (!i.buildingTypeCommercial) return 'Commercial building type is required.'
    if (!i.totalAreaCommercial || !i.numberOfFloors)
      return 'Total area and number of floors are required for commercial property.'
  }
  return ''
}
export function validateBrokerage(i: CreateBrokerageInput) {
  if (!i.title.trim() || !i.location.trim() || !i.ownerName.trim())
    return 'Title, location and owner / mandate giver are required.'
  if (!Number.isFinite(i.price) || i.price <= 0) return 'Asking price must be greater than zero.'
  if (i.commissionRate < 0 || i.commissionRate > 100)
    return 'Commission rate must be between 0 and 100%.'
  return ''
}
