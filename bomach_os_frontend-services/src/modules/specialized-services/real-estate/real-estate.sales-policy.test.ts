import { describe, expect, it } from 'vitest'

import type { CreateEstateInput } from './real-estate.types'
import { validateEstate } from './real-estate.validation'

const estate = (): CreateEstateInput => ({
  isOurEstate: true,
  estateName: 'Policy Estate',
  estateCode: 'POLICY-001',
  estateType: 'residential',
  developerCompanyName: 'Bomach',
  estateDescription: 'Policy validation fixture',
  country: 'Nigeria',
  countryCode: 'NGA',
  state: 'Lagos',
  cityTown: 'Lekki, Eti-Osa',
  preciseAddress: 'Lekki',
  boundary: {},
  estateMapUrl: '',
  virtualTourUrl: '',
  hasCOfO: false,
  hasDeedOfAssignment: false,
  hasSurveyPlan: false,
  zoningInformation: '',
  hasPlanningPermit: false,
  hasBuildingApproval: false,
  hasEnvironmentalClearance: false,
  pricePerSqm: 100000,
  availablePlotSizes: '',
  minPriceOtherProperties: null,
  maxPriceOtherProperties: null,
  estateStatus: 'available',
  totalArea: null,
  areaUnit: 'sqm',
  hasRoads: false,
  hasElectricity: false,
  hasWater: false,
  hasFencing: false,
  hasSecurity: false,
  hasDrainage: false,
  hasRecreation: false,
  legalFee: null,
  developmentFee: null,
  receiptFee: null,
  reservationAllowed: false,
  reservationThresholdPercent: null,
  installmentAllowed: false,
  maxInstallmentMonths: null,
  reservationPaymentWindowHours: 72,
  tags: [],
  documents: [],
})

describe('Estate sales policy', () => {
  it('accepts conservative defaults', () => {
    expect(validateEstate(estate())).toBe('')
  })

  it('requires a threshold for reservation', () => {
    const input = estate()
    input.reservationAllowed = true
    expect(validateEstate(input)).toContain('Reservation down payment')
  })

  it('accepts valid reservation and installment settings', () => {
    const input = estate()
    input.reservationAllowed = true
    input.reservationThresholdPercent = 20
    input.installmentAllowed = true
    input.maxInstallmentMonths = 12
    input.reservationPaymentWindowHours = 48
    expect(validateEstate(input)).toBe('')
  })

  it('rejects max months when installments are disabled', () => {
    const input = estate()
    input.maxInstallmentMonths = 12
    expect(validateEstate(input)).toContain('must be empty')
  })
})
