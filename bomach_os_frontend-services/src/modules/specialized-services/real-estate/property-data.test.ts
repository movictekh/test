import { describe, expect, it } from 'vitest'

import type { Property } from './real-estate.types'
import { parsePropertySheetMatrix, PROPERTY_CLEAR_TOKEN } from './property-data'

const existingPlot = (): Property => ({
  id: 41,
  isOurProperty: true,
  estateId: 3,
  estateName: 'Oak Estate',
  estateCode: 'OAK',
  propertyType: 'plot',
  propertyTypeDisplay: 'Plot of Land',
  propertyName: 'Plot A-01',
  price: 5000000,
  boundary: {},
  description: 'Original',
  status: 'available',
  statusDisplay: 'Available',
  plotNumber: 1,
  clientName: '',
  plotSize: 500,
  plotSizeUnit: 'sqm',
  buildingTypeResidential: '',
  buildingTypeResidentialDisplay: '',
  bedrooms: null,
  bathrooms: null,
  floorsResidential: null,
  totalAreaResidential: null,
  buildingTypeCommercial: '',
  buildingTypeCommercialDisplay: '',
  totalAreaCommercial: null,
  numberOfFloors: null,
  unitsOffices: null,
  images: [],
  isActive: true,
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
})

describe('property data studio parser', () => {
  it('accepts valid create rows and lets Estate pricing fill a blank price', () => {
    const result = parsePropertySheetMatrix(
      [
        ['property_type', 'property_name', 'price', 'plot_size', 'plot_size_unit'],
        ['plot', 'Plot A-01', '', 500, 'sqm'],
      ],
      'create',
    )

    expect(result.fileErrors).toEqual([])
    expect(result.rows).toHaveLength(1)
    expect(result.rows[0].status).toBe('ready')
    expect(result.rows[0].input?.price).toBeNull()
    expect(result.rows[0].warnings[0]).toContain('Estate default price')
  })

  it('rejects incomplete boundary pairs', () => {
    const result = parsePropertySheetMatrix(
      [
        ['property_type', 'property_name', 'plot_size', 'boundary_nw_lat', 'boundary_nw_lng'],
        ['plot', 'Plot A-01', 500, 6.4, ''],
      ],
      'create',
    )

    expect(result.rows[0].status).toBe('invalid')
    expect(result.rows[0].errors.join(' ')).toContain('requires both latitude and longitude')
  })

  it('rejects Reserved and Sold state in create import', () => {
    const result = parsePropertySheetMatrix(
      [
        ['property_type', 'property_name', 'plot_size', 'status'],
        ['plot', 'Plot A-01', 500, 'reserved'],
      ],
      'create',
    )

    expect(result.rows[0].status).toBe('invalid')
    expect(result.rows[0].errors.join(' ')).toContain('purchase/payment workflow')
  })

  it('builds an edit diff and leaves blank cells unchanged', () => {
    const result = parsePropertySheetMatrix(
      [
        ['property_id', 'property_type', 'property_name', 'price', 'description'],
        [41, 'plot', '', 6500000, ''],
      ],
      'edit',
      [existingPlot()],
    )

    expect(result.rows[0].status).toBe('ready')
    expect(result.rows[0].patch).toEqual({ price: 6500000 })
    expect(result.rows[0].diffs).toHaveLength(1)
    expect(result.rows[0].diffs[0].label).toBe('Price')
  })

  it('supports explicit description clearing without treating blanks as clears', () => {
    const result = parsePropertySheetMatrix(
      [
        ['property_id', 'description'],
        [41, PROPERTY_CLEAR_TOKEN],
      ],
      'edit',
      [existingPlot()],
    )

    expect(result.rows[0].status).toBe('ready')
    expect(result.rows[0].patch.description).toBe('')
  })

  it('marks unchanged exported edit rows as skipped', () => {
    const result = parsePropertySheetMatrix(
      [
        ['property_id', 'property_type', 'property_name', 'price'],
        [41, 'plot', 'Plot A-01', 5000000],
      ],
      'edit',
      [existingPlot()],
    )

    expect(result.rows[0].status).toBe('skipped')
    expect(result.rows[0].selected).toBe(false)
  })

  it('rejects duplicate property ids in one edit file', () => {
    const result = parsePropertySheetMatrix(
      [
        ['property_id', 'price'],
        [41, 6000000],
        [41, 7000000],
      ],
      'edit',
      [existingPlot()],
    )

    expect(result.rows.every((row) => row.status === 'invalid')).toBe(true)
    expect(result.rows[1].errors.join(' ')).toContain('appears more than once')
  })

  it('rejects bulk commercial-state transitions on edit', () => {
    const result = parsePropertySheetMatrix(
      [
        ['property_id', 'status'],
        [41, 'sold'],
      ],
      'edit',
      [existingPlot()],
    )

    expect(result.rows[0].status).toBe('invalid')
    expect(result.rows[0].errors.join(' ')).toContain('purchase/payment workflow')
  })

  it('rejects a property id that is not in the selected Estate', () => {
    const result = parsePropertySheetMatrix(
      [
        ['property_id', 'price'],
        [999, 6000000],
      ],
      'edit',
      [existingPlot()],
    )

    expect(result.rows[0].status).toBe('invalid')
    expect(result.rows[0].errors.join(' ')).toContain('selected Estate')
  })

  it('reports duplicate normalized headers as a file error', () => {
    const result = parsePropertySheetMatrix(
      [
        ['property id', 'property_id', 'price'],
        [41, 41, 6000000],
      ],
      'edit',
      [existingPlot()],
    )

    expect(result.fileErrors.join(' ')).toContain('Duplicate column')
  })

  it('does not permit prototype-polluting spreadsheet headers to alter Object.prototype', () => {
    const before = ({} as { polluted?: unknown }).polluted
    const result = parsePropertySheetMatrix(
      [
        ['__proto__', 'property_type', 'property_name', 'plot_size'],
        ['polluted', 'plot', 'Plot A-02', 500],
      ],
      'create',
    )

    expect(result.rows[0].status).toBe('ready')
    expect(({} as { polluted?: unknown }).polluted).toBe(before)
    expect(result.warnings.join(' ')).toContain('__proto__')
  })
})
