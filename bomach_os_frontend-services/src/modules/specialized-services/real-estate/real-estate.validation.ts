import type {
  CreateBrokerageInput,
  CreateEstateInput,
  CreatePropertyInput,
  QuickUpdatePlotInput,
} from './real-estate.types'
import { validateBoundary } from './real-estate.boundary'
export function validateQuickPlotUpdate(i: QuickUpdatePlotInput) {
  if (i.price !== undefined && (!Number.isFinite(i.price) || i.price <= 0))
    return 'Plot price must be greater than zero.'
  if (i.status === 'reserved' || i.status === 'sold')
    return 'Reserved and sold states are controlled by verified purchase payments.'
  return ''
}
export function validateEstate(i: CreateEstateInput) {
  if (!i.estateName.trim()) return 'Estate name is required.'
  if (!i.estateCode.trim()) return 'Estate code is required.'
  if (!i.developerCompanyName.trim()) return 'Developer / company name is required.'
  if (!i.estateDescription.trim()) return 'Estate description is required.'
  if (!i.country.trim() || !i.state.trim() || !i.cityTown.trim() || !i.preciseAddress.trim())
    return 'Complete Estate location is required.'
  const boundaryError = validateBoundary(i.boundary)
  if (boundaryError) return boundaryError
  if (!Number.isFinite(i.pricePerSqm) || i.pricePerSqm < 0)
    return 'Price per square metre must be zero or greater.'
  if (
    i.minPriceOtherProperties != null &&
    i.maxPriceOtherProperties != null &&
    i.minPriceOtherProperties > i.maxPriceOtherProperties
  )
    return 'Minimum property price cannot exceed maximum property price.'
  if (i.reservationAllowed) {
    if (
      i.reservationThresholdPercent == null ||
      !Number.isFinite(i.reservationThresholdPercent) ||
      i.reservationThresholdPercent <= 0 ||
      i.reservationThresholdPercent > 100
    )
      return 'Reservation down payment must be greater than 0% and at most 100%.'
  } else if (i.reservationThresholdPercent != null) {
    return 'Reservation down payment must be empty when reservation is disabled.'
  }
  if (
    i.installmentAllowed &&
    i.maxInstallmentMonths != null &&
    (!Number.isInteger(i.maxInstallmentMonths) || i.maxInstallmentMonths < 1)
  )
    return 'Maximum installment months must be a positive whole number.'
  if (!i.installmentAllowed && i.maxInstallmentMonths != null)
    return 'Maximum installment months must be empty when installment payment is disabled.'
  if (!Number.isInteger(i.reservationPaymentWindowHours) || i.reservationPaymentWindowHours < 1)
    return 'Reservation payment window must be at least 1 hour.'
  if (i.virtualTourUrl?.trim()) {
    try {
      new URL(i.virtualTourUrl)
    } catch {
      return 'Virtual tour link must be a valid URL.'
    }
  }
  return ''
}
export function validateProperty(i: CreatePropertyInput, options?: { requirePrice?: boolean }) {
  if (!i.propertyName.trim()) return 'Property name is required.'
  const boundaryError = validateBoundary(i.boundary)
  if (boundaryError) return boundaryError
  const requirePrice = options?.requirePrice ?? true
  if (requirePrice && (i.price == null || !Number.isFinite(i.price) || i.price <= 0))
    return 'Property price must be greater than zero.'
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
  const boundaryError = validateBoundary(i.boundary)
  if (boundaryError) return boundaryError
  if (!i.title.trim() || !i.location.trim() || !i.ownerName.trim())
    return 'Title, location and owner / mandate giver are required.'
  if (!Number.isFinite(i.price) || i.price <= 0) return 'Asking price must be greater than zero.'
  if (i.commissionRate < 0 || i.commissionRate > 100)
    return 'Commission rate must be between 0 and 100%.'
  return ''
}
