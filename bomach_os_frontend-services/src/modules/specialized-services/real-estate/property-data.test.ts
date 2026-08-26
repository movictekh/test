import { describe, expect, it } from 'vitest'

import type { Property } from './real-estate.types'
import {
  parsePropertySheetMatrix,
  PROPERTY_CLEAR_TOKEN,
  PROPERTY_DATA_MAX_ROWS,
  readPropertyWorkbook,
} from './property-data'

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

type ParsedSheetResult = ReturnType<typeof parsePropertySheetMatrix>
type LoadedWorkbook = Awaited<ReturnType<typeof readPropertyWorkbook>>

function rowAt(result: ParsedSheetResult, index = 0) {
  const row = result.rows[index]
  if (!row) throw new Error(`Expected parsed row at index ${index}.`)
  return row
}

function sheetAt(workbook: LoadedWorkbook, index = 0) {
  const sheet = workbook.sheets[index]
  if (!sheet) throw new Error(`Expected worksheet at index ${index}.`)
  return sheet
}

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
    expect(rowAt(result).status).toBe('ready')
    expect(rowAt(result).input?.price).toBeNull()
    expect(rowAt(result).warnings[0]).toContain('Estate default price')
  })

  it('rejects incomplete boundary pairs', () => {
    const result = parsePropertySheetMatrix(
      [
        ['property_type', 'property_name', 'plot_size', 'boundary_nw_lat', 'boundary_nw_lng'],
        ['plot', 'Plot A-01', 500, 6.4, ''],
      ],
      'create',
    )

    expect(rowAt(result).status).toBe('invalid')
    expect(rowAt(result).errors.join(' ')).toContain('requires both latitude and longitude')
  })

  it('rejects Reserved and Sold state in create import', () => {
    const result = parsePropertySheetMatrix(
      [
        ['property_type', 'property_name', 'plot_size', 'status'],
        ['plot', 'Plot A-01', 500, 'reserved'],
      ],
      'create',
    )

    expect(rowAt(result).status).toBe('invalid')
    expect(rowAt(result).errors.join(' ')).toContain('purchase/payment workflow')
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

    expect(rowAt(result).status).toBe('ready')
    expect(rowAt(result).patch).toEqual({ price: 6500000 })
    expect(rowAt(result).diffs).toHaveLength(1)
    const firstDiff = rowAt(result).diffs.at(0)
    expect(firstDiff?.label).toBe('Price')
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

    expect(rowAt(result).status).toBe('ready')
    expect(rowAt(result).patch.description).toBe('')
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

    expect(rowAt(result).status).toBe('skipped')
    expect(rowAt(result).selected).toBe(false)
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
    expect(rowAt(result, 1).errors.join(' ')).toContain('appears more than once')
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

    expect(rowAt(result).status).toBe('invalid')
    expect(rowAt(result).errors.join(' ')).toContain('purchase/payment workflow')
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

    expect(rowAt(result).status).toBe('invalid')
    expect(rowAt(result).errors.join(' ')).toContain('selected Estate')
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

  it('uses prototype-less records for untrusted spreadsheet headers', () => {
    const result = parsePropertySheetMatrix(
      [
        ['__proto__', 'property_type', 'property_name', 'plot_size'],
        ['polluted', 'plot', 'Plot A-02', 500],
      ],
      'create',
    )

    expect(rowAt(result).status).toBe('ready')
    expect(Object.getPrototypeOf(rowAt(result).raw)).toBeNull()
    expect(result.warnings.join(' ')).toContain('proto')
  })

  it('rejects imports larger than the per-session row limit', () => {
    const matrix = [
      ['property_type', 'property_name', 'plot_size'],
      ...Array.from({ length: PROPERTY_DATA_MAX_ROWS + 1 }, (_, index) => [
        'plot',
        `Plot ${index + 1}`,
        500,
      ]),
    ]

    const result = parsePropertySheetMatrix(matrix, 'create')
    expect(result.rows).toEqual([])
    expect(result.fileErrors.join(' ')).toContain('maximum')
  })

  it('parses a real CSV file through SheetJS', async () => {
    const csv = [
      'property_type,property_name,price,plot_size,plot_size_unit',
      'plot,Plot CSV-01,,500,sqm',
    ].join('\n')
    const file = new File([csv], 'properties.csv', { type: 'text/csv' })

    const workbook = await readPropertyWorkbook(file)
    const parsed = parsePropertySheetMatrix(sheetAt(workbook).matrix, 'create')

    expect(workbook.sheets).toHaveLength(1)
    expect(parsed.rows).toHaveLength(1)
    expect(rowAt(parsed).status).toBe('ready')
    expect(rowAt(parsed).propertyName).toBe('Plot CSV-01')
  })

  it('parses a real XLSX file through SheetJS', async () => {
    const XLSX = await import('xlsx')
    const workbook = XLSX.utils.book_new()
    const sheet = XLSX.utils.aoa_to_sheet([
      ['property_type', 'property_name', 'price', 'plot_size', 'plot_size_unit'],
      ['plot', 'Plot XLSX-01', '', 500, 'sqm'],
    ])
    XLSX.utils.book_append_sheet(workbook, sheet, 'Properties')
    const rawBytes: unknown = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' })
    let bytes: ArrayBuffer
    if (rawBytes instanceof ArrayBuffer) {
      bytes = rawBytes
    } else if (ArrayBuffer.isView(rawBytes)) {
      const copy = new Uint8Array(rawBytes.byteLength)
      copy.set(new Uint8Array(rawBytes.buffer, rawBytes.byteOffset, rawBytes.byteLength))
      bytes = copy.buffer
    } else {
      throw new Error('SheetJS did not return binary XLSX data.')
    }

    const file = new File([bytes], 'properties.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })

    const parsedWorkbook = await readPropertyWorkbook(file)
    const parsed = parsePropertySheetMatrix(sheetAt(parsedWorkbook).matrix, 'create')

    expect(sheetAt(parsedWorkbook).name).toBe('Properties')
    expect(parsed.rows).toHaveLength(1)
    expect(rowAt(parsed).status).toBe('ready')
    expect(rowAt(parsed).propertyName).toBe('Plot XLSX-01')
  })
})
