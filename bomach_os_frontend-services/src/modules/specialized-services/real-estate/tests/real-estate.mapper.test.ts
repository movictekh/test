import { describe, expect, it } from 'vitest'
import { mapEstateList, mapEstateStats, mapPlotLayoutItem } from '../real-estate.mapper'

describe('real estate mappers', () => {
  it('maps paginated estate responses', () => {
    const result = mapEstateList({ count: 1, items: [{ id: 7, is_our_estate: true, estate_name: 'Riverside Estate', estate_code: 'EST-007', estate_type: 'residential', estate_type_display: 'Residential', developer_company_name: 'Bomach', estate_description: 'Residential estate', country: 'Nigeria', state: 'Enugu', city_town: 'Enugu', precise_address: 'Independence Layout', price_per_sqm: '50000.00', estate_status: 'available', estate_status_display: 'Available', area_unit: 'sqm', amenities: ['Roads'], title_documents: ['Survey Plan'], government_approvals: [], tags: [], documents: [], is_active: true }] })
    expect(result.count).toBe(1)
    expect(result.items[0]?.estateCode).toBe('EST-007')
    expect(result.items[0]?.pricePerSqm).toBe(50000)
  })

  it('maps stats decimals into numbers', () => {
    expect(mapEstateStats({ total: 50, sold: 12, reserved: 5, available: 31, hold: 2, not_for_sale: 0, total_value: '250000000.00', sold_value: '60000000.00' })).toEqual({ total: 50, sold: 12, reserved: 5, available: 31, hold: 2, notForSale: 0, totalValue: 250000000, soldValue: 60000000 })
  })

  it('maps the lightweight plot layout contract', () => {
    expect(mapPlotLayoutItem({ id: 5, plot_number: 12, property_name: 'Plot 12', status: 'reserved', status_display: 'Reserved', plot_size: '500.00', price: '5000000.00', client_name: 'Ada Okafor' })).toEqual({ id: 5, plotNumber: 12, propertyName: 'Plot 12', status: 'reserved', statusDisplay: 'Reserved', plotSize: 500, price: 5000000, clientName: 'Ada Okafor' })
  })
})
