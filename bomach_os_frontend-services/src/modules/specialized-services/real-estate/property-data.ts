import type {
  Boundary,
  BoundaryCorner,
  CreatePropertyInput,
  Property,
  PropertyStatus,
  PropertyType,
} from './real-estate.types'
import { validateProperty } from './real-estate.validation'

export const PROPERTY_DATA_MAX_ROWS = 500
export const PROPERTY_DATA_CONCURRENCY = 4
export const PROPERTY_CLEAR_TOKEN = '__CLEAR__'

export type PropertyDataMode = 'create' | 'edit'
export type PropertyDataRowStatus =
  'ready' | 'invalid' | 'skipped' | 'submitting' | 'success' | 'failed'

export interface PropertyDataDiff {
  field: string
  label: string
  before: string
  after: string
}

export interface PropertyDataRow {
  key: string
  rowNumber: number
  propertyId: number | null
  propertyName: string
  propertyType: PropertyType | null
  raw: Record<string, unknown>
  input: CreatePropertyInput | null
  patch: Partial<CreatePropertyInput>
  errors: string[]
  warnings: string[]
  diffs: PropertyDataDiff[]
  selected: boolean
  status: PropertyDataRowStatus
  resultPropertyId: number | null
  error: string
}

export interface PropertySheetResult {
  headers: string[]
  rows: PropertyDataRow[]
  fileErrors: string[]
  warnings: string[]
}

export interface PropertyWorkbookData {
  filename: string
  sheets: Array<{
    name: string
    matrix: unknown[][]
  }>
}

const corners: BoundaryCorner[] = ['nw', 'ne', 'se', 'sw']

export const propertyCreateHeaders = [
  'property_type',
  'property_name',
  'price',
  'description',
  'status',
  'is_our_property',
  'boundary_nw_lat',
  'boundary_nw_lng',
  'boundary_ne_lat',
  'boundary_ne_lng',
  'boundary_se_lat',
  'boundary_se_lng',
  'boundary_sw_lat',
  'boundary_sw_lng',
  'plot_number',
  'plot_size',
  'plot_size_unit',
  'building_type_residential',
  'bedrooms',
  'bathrooms',
  'floors_residential',
  'total_area_residential',
  'building_type_commercial',
  'total_area_commercial',
  'number_of_floors',
  'units_offices',
] as const

export const propertyEditHeaders = ['property_id', ...propertyCreateHeaders] as const

const createRequiredHeaders = ['property_type', 'property_name']
const editRequiredHeaders = ['property_id']

const propertyTypeAliases: Record<string, PropertyType> = {
  plot: 'plot',
  land: 'plot',
  'plot of land': 'plot',
  residential: 'residential',
  'residential building': 'residential',
  commercial: 'commercial',
  'commercial building': 'commercial',
}

const statusAliases: Record<string, PropertyStatus> = {
  available: 'available',
  hold: 'hold',
  'not-for-sale': 'not-for-sale',
  'not for sale': 'not-for-sale',
  nfs: 'not-for-sale',
  reserved: 'reserved',
  sold: 'sold',
}

const residentialTypeAliases: Record<string, string> = {
  house: 'house',
  villa: 'villa',
  apartment: 'apartment',
  townhouse: 'townhouse',
  duplex: 'duplex',
  bungalow: 'bungalow',
  penthouse: 'penthouse',
}

const commercialTypeAliases: Record<string, string> = {
  office: 'office',
  retail: 'retail',
  'retail space': 'retail',
  warehouse: 'warehouse',
  'shopping mall': 'shopping_mall',
  shopping_mall: 'shopping_mall',
  hotel: 'hotel',
  'mixed use': 'mixed_use',
  mixed_use: 'mixed_use',
}

const areaUnitAliases: Record<string, string> = {
  sqm: 'sqm',
  'square meter': 'sqm',
  'square meters': 'sqm',
  'square metre': 'sqm',
  'square metres': 'sqm',
  sqft: 'sqft',
  'square foot': 'sqft',
  'square feet': 'sqft',
  acre: 'acres',
  acres: 'acres',
  hectare: 'hectares',
  hectares: 'hectares',
}

const residentialFields = [
  'building_type_residential',
  'bedrooms',
  'bathrooms',
  'floors_residential',
  'total_area_residential',
]
const commercialFields = [
  'building_type_commercial',
  'total_area_commercial',
  'number_of_floors',
  'units_offices',
]
const plotFields = ['plot_number', 'plot_size', 'plot_size_unit']

const fieldLabels: Record<string, string> = {
  propertyName: 'Property name',
  price: 'Price',
  description: 'Description',
  status: 'Status',
  isOurProperty: 'Ownership flag',
  boundary: 'Boundary',
  plotNumber: 'Plot number',
  plotSize: 'Plot size',
  plotSizeUnit: 'Plot size unit',
  buildingTypeResidential: 'Residential type',
  bedrooms: 'Bedrooms',
  bathrooms: 'Bathrooms',
  floorsResidential: 'Residential floors',
  totalAreaResidential: 'Residential total area',
  buildingTypeCommercial: 'Commercial type',
  totalAreaCommercial: 'Commercial total area',
  numberOfFloors: 'Commercial floors',
  unitsOffices: 'Units / offices',
}

function stringifyCellValue(value: unknown) {
  if (value == null) return ''
  if (
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'bigint' ||
    typeof value === 'boolean'
  )
    return String(value)
  if (value instanceof Date) return value.toISOString()
  try {
    return JSON.stringify(value) ?? ''
  } catch {
    return ''
  }
}

function normalizeHeader(value: unknown) {
  return stringifyCellValue(value)
    .trim()
    .toLowerCase()
    .replace(/[%()]/g, '')
    .replace(/[\s/-]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '')
}

function text(value: unknown) {
  return stringifyCellValue(value).trim()
}

function normalizedText(value: unknown) {
  return text(value).toLowerCase().replace(/\s+/g, ' ')
}

function isBlank(value: unknown) {
  return value == null || text(value) === ''
}

function isClear(value: unknown) {
  return text(value).toUpperCase() === PROPERTY_CLEAR_TOKEN
}

function normalizeNumericText(value: unknown) {
  return text(value).replace(/,/g, '')
}

function parseNumber(
  value: unknown,
  label: string,
  errors: string[],
  options: { integer?: boolean; min?: number; max?: number } = {},
) {
  if (isBlank(value)) return undefined
  if (isClear(value)) {
    errors.push(`${label} cannot use ${PROPERTY_CLEAR_TOKEN}.`)
    return undefined
  }
  const parsed = Number(normalizeNumericText(value))
  if (!Number.isFinite(parsed)) {
    errors.push(`${label} must be a valid number.`)
    return undefined
  }
  if (options.integer && !Number.isInteger(parsed)) {
    errors.push(`${label} must be a whole number.`)
    return undefined
  }
  if (options.min != null && parsed < options.min) {
    errors.push(`${label} must be at least ${options.min}.`)
    return undefined
  }
  if (options.max != null && parsed > options.max) {
    errors.push(`${label} must be at most ${options.max}.`)
    return undefined
  }
  return parsed
}

function parseBoolean(value: unknown, label: string, errors: string[]) {
  if (isBlank(value)) return undefined
  const normalized = normalizedText(value)
  if (['true', 'yes', 'y', '1'].includes(normalized)) return true
  if (['false', 'no', 'n', '0'].includes(normalized)) return false
  errors.push(`${label} must be yes/no, true/false or 1/0.`)
  return undefined
}

function parseAlias<T extends string>(
  value: unknown,
  label: string,
  aliases: Record<string, T>,
  errors: string[],
) {
  if (isBlank(value)) return undefined
  const normalized = normalizedText(value)
  const matched = aliases[normalized]
  if (matched) return matched
  errors.push(`${label} has an unsupported value: "${text(value)}".`)
  return undefined
}

function hasAnyValue(row: Record<string, unknown>, fields: string[]) {
  return fields.some((field) => !isBlank(row[field]))
}

function parseBoundary(
  row: Record<string, unknown>,
  mode: PropertyDataMode,
  errors: string[],
  base: Boundary = {},
) {
  let touched = false
  const boundary: Boundary = { ...base }

  for (const corner of corners) {
    const latKey = `boundary_${corner}_lat`
    const lngKey = `boundary_${corner}_lng`
    const latRaw = row[latKey]
    const lngRaw = row[lngKey]

    if (isBlank(latRaw) && isBlank(lngRaw)) continue
    touched = true

    if (mode === 'edit' && isClear(latRaw) && isClear(lngRaw)) {
      delete boundary[corner]
      continue
    }

    if (isClear(latRaw) || isClear(lngRaw)) {
      errors.push(
        `${corner.toUpperCase()} boundary must use ${PROPERTY_CLEAR_TOKEN} for both latitude and longitude when clearing a corner.`,
      )
      continue
    }

    if (isBlank(latRaw) || isBlank(lngRaw)) {
      errors.push(
        `${corner.toUpperCase()} boundary requires both latitude and longitude when supplied.`,
      )
      continue
    }

    const lat = parseNumber(latRaw, `${corner.toUpperCase()} latitude`, errors, {
      min: -90,
      max: 90,
    })
    const lng = parseNumber(lngRaw, `${corner.toUpperCase()} longitude`, errors, {
      min: -180,
      max: 180,
    })
    if (lat != null && lng != null) boundary[corner] = { lat, lng }
  }

  return { touched, boundary }
}

function propertyToInput(property: Property): CreatePropertyInput {
  return {
    isOurProperty: property.isOurProperty,
    propertyType: property.propertyType,
    propertyName: property.propertyName,
    price: property.price,
    boundary: property.boundary,
    description: property.description,
    status: property.status,
    plotNumber: property.plotNumber,
    clientName: property.clientName,
    plotSize: property.plotSize,
    plotSizeUnit: property.plotSizeUnit,
    buildingTypeResidential: property.buildingTypeResidential,
    bedrooms: property.bedrooms,
    bathrooms: property.bathrooms,
    floorsResidential: property.floorsResidential,
    totalAreaResidential: property.totalAreaResidential,
    buildingTypeCommercial: property.buildingTypeCommercial,
    totalAreaCommercial: property.totalAreaCommercial,
    numberOfFloors: property.numberOfFloors,
    unitsOffices: property.unitsOffices,
  }
}

function displayValue(value: unknown) {
  if (value == null || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return stringifyCellValue(value) || '—'
}

function buildDiffs(existing: Property, patch: Partial<CreatePropertyInput>) {
  const before = propertyToInput(existing) as unknown as Record<string, unknown>
  const next = patch as unknown as Record<string, unknown>
  return Object.keys(next).map((field) => ({
    field,
    label: fieldLabels[field] ?? field,
    before: displayValue(before[field]),
    after: displayValue(next[field]),
  }))
}

function invalidRow(
  rowNumber: number,
  raw: Record<string, unknown>,
  errors: string[],
  propertyId: number | null = null,
  propertyName = '',
  propertyType: PropertyType | null = null,
): PropertyDataRow {
  return {
    key: `${rowNumber}-${(propertyId ?? propertyName) || 'row'}`,
    rowNumber,
    propertyId,
    propertyName,
    propertyType,
    raw,
    input: null,
    patch: {},
    errors,
    warnings: [],
    diffs: [],
    selected: false,
    status: 'invalid',
    resultPropertyId: null,
    error: '',
  }
}

function parseCreateRow(rowNumber: number, row: Record<string, unknown>): PropertyDataRow {
  const errors: string[] = []
  const warnings: string[] = []
  const propertyType =
    parseAlias(row.property_type, 'Property type', propertyTypeAliases, errors) ?? null
  const propertyName = text(row.property_name)

  if (!propertyName) errors.push('Property name is required.')

  if (propertyType !== 'plot' && hasAnyValue(row, plotFields))
    errors.push('Plot-only columns must be blank for non-plot properties.')
  if (propertyType !== 'residential' && hasAnyValue(row, residentialFields))
    errors.push('Residential-only columns must be blank for non-residential properties.')
  if (propertyType !== 'commercial' && hasAnyValue(row, commercialFields))
    errors.push('Commercial-only columns must be blank for non-commercial properties.')

  const price = parseNumber(row.price, 'Price', errors, { min: 0.01 })
  const isOurProperty = parseBoolean(row.is_our_property, 'Is our property', errors) ?? true
  const status = parseAlias(row.status, 'Status', statusAliases, errors) ?? 'available'

  if (status === 'reserved' || status === 'sold') {
    errors.push(
      'Bulk import cannot create Reserved or Sold state. Those commercial states belong to the purchase/payment workflow.',
    )
  }

  const { boundary } = parseBoundary(row, 'create', errors)

  const input: CreatePropertyInput = {
    isOurProperty,
    propertyType: propertyType ?? 'plot',
    propertyName,
    price: price ?? null,
    boundary,
    description: text(row.description),
    status,
  }

  if (propertyType === 'plot') {
    input.plotNumber = parseNumber(row.plot_number, 'Plot number', errors, {
      integer: true,
      min: 1,
    })
    input.plotSize = parseNumber(row.plot_size, 'Plot size', errors, { min: 0.01 })
    input.plotSizeUnit =
      parseAlias(row.plot_size_unit, 'Plot size unit', areaUnitAliases, errors) ?? 'sqm'
  }

  if (propertyType === 'residential') {
    input.buildingTypeResidential =
      parseAlias(
        row.building_type_residential,
        'Residential building type',
        residentialTypeAliases,
        errors,
      ) ?? ''
    input.bedrooms = parseNumber(row.bedrooms, 'Bedrooms', errors, { integer: true, min: 1 })
    input.bathrooms = parseNumber(row.bathrooms, 'Bathrooms', errors, {
      integer: true,
      min: 1,
    })
    input.floorsResidential = parseNumber(row.floors_residential, 'Residential floors', errors, {
      integer: true,
      min: 1,
    })
    input.totalAreaResidential = parseNumber(
      row.total_area_residential,
      'Residential total area',
      errors,
      { min: 0.01 },
    )
  }

  if (propertyType === 'commercial') {
    input.buildingTypeCommercial =
      parseAlias(
        row.building_type_commercial,
        'Commercial building type',
        commercialTypeAliases,
        errors,
      ) ?? ''
    input.totalAreaCommercial = parseNumber(
      row.total_area_commercial,
      'Commercial total area',
      errors,
      { min: 0.01 },
    )
    input.numberOfFloors = parseNumber(row.number_of_floors, 'Number of floors', errors, {
      integer: true,
      min: 1,
    })
    input.unitsOffices = parseNumber(row.units_offices, 'Units / offices', errors, {
      integer: true,
      min: 0,
    })
  }

  const validationError = validateProperty(input, { requirePrice: false })
  if (validationError && !errors.includes(validationError)) errors.push(validationError)

  if (price == null)
    warnings.push('Price is blank; the selected Estate default price will be used.')

  if (errors.length)
    return {
      ...invalidRow(rowNumber, row, errors, null, propertyName, propertyType),
      warnings,
    }

  return {
    key: `${rowNumber}-${propertyName}`,
    rowNumber,
    propertyId: null,
    propertyName,
    propertyType,
    raw: row,
    input,
    patch: {},
    errors: [],
    warnings,
    diffs: [],
    selected: true,
    status: 'ready',
    resultPropertyId: null,
    error: '',
  }
}

function parseEditRow(
  rowNumber: number,
  row: Record<string, unknown>,
  existingById: Map<number, Property>,
): PropertyDataRow {
  const errors: string[] = []
  const warnings: string[] = []
  const propertyId = parseNumber(row.property_id, 'Property ID', errors, {
    integer: true,
    min: 1,
  })
  if (propertyId == null) return invalidRow(rowNumber, row, errors)

  const existing = existingById.get(propertyId)
  if (!existing) {
    errors.push(`Property ID ${propertyId} does not belong to the selected Estate.`)
    return invalidRow(rowNumber, row, errors, propertyId)
  }

  const patch: Partial<CreatePropertyInput> = {}
  const suppliedType = parseAlias(row.property_type, 'Property type', propertyTypeAliases, errors)
  if (suppliedType && suppliedType !== existing.propertyType) {
    errors.push('Bulk edit cannot change property type. Edit the property individually instead.')
  }

  if (existing.propertyType !== 'plot' && hasAnyValue(row, plotFields))
    errors.push('Plot-only columns must be blank for non-plot properties.')
  if (existing.propertyType !== 'residential' && hasAnyValue(row, residentialFields))
    errors.push('Residential-only columns must be blank for non-residential properties.')
  if (existing.propertyType !== 'commercial' && hasAnyValue(row, commercialFields))
    errors.push('Commercial-only columns must be blank for non-commercial properties.')

  if (!isBlank(row.property_name)) {
    if (isClear(row.property_name)) errors.push('Property name cannot be cleared.')
    else patch.propertyName = text(row.property_name)
  }

  if (!isBlank(row.price)) {
    const value = parseNumber(row.price, 'Price', errors, { min: 0.01 })
    if (value != null) patch.price = value
  }

  if (!isBlank(row.description)) {
    patch.description = isClear(row.description) ? '' : text(row.description)
  }

  if (!isBlank(row.status)) {
    const targetStatus = parseAlias(row.status, 'Status', statusAliases, errors)
    if (targetStatus && targetStatus !== existing.status) {
      if (
        existing.status === 'reserved' ||
        existing.status === 'sold' ||
        targetStatus === 'reserved' ||
        targetStatus === 'sold'
      ) {
        errors.push(
          'Bulk edit cannot create, release or alter Reserved/Sold state. Use the commercial purchase/payment workflow.',
        )
      } else {
        patch.status = targetStatus
      }
    }
  }

  if (!isBlank(row.is_our_property)) {
    const value = parseBoolean(row.is_our_property, 'Is our property', errors)
    if (value != null) patch.isOurProperty = value
  }

  const boundaryResult = parseBoundary(row, 'edit', errors, existing.boundary)
  if (boundaryResult.touched) patch.boundary = boundaryResult.boundary

  if (existing.propertyType === 'plot') {
    if (!isBlank(row.plot_number)) {
      const value = parseNumber(row.plot_number, 'Plot number', errors, {
        integer: true,
        min: 1,
      })
      if (value != null) patch.plotNumber = value
    }
    if (!isBlank(row.plot_size)) {
      const value = parseNumber(row.plot_size, 'Plot size', errors, { min: 0.01 })
      if (value != null) patch.plotSize = value
    }
    if (!isBlank(row.plot_size_unit)) {
      const value = parseAlias(row.plot_size_unit, 'Plot size unit', areaUnitAliases, errors)
      if (value) patch.plotSizeUnit = value
    }
  }

  if (existing.propertyType === 'residential') {
    if (!isBlank(row.building_type_residential)) {
      const value = parseAlias(
        row.building_type_residential,
        'Residential building type',
        residentialTypeAliases,
        errors,
      )
      if (value) patch.buildingTypeResidential = value
    }
    if (!isBlank(row.bedrooms)) {
      const value = parseNumber(row.bedrooms, 'Bedrooms', errors, { integer: true, min: 1 })
      if (value != null) patch.bedrooms = value
    }
    if (!isBlank(row.bathrooms)) {
      const value = parseNumber(row.bathrooms, 'Bathrooms', errors, {
        integer: true,
        min: 1,
      })
      if (value != null) patch.bathrooms = value
    }
    if (!isBlank(row.floors_residential)) {
      const value = parseNumber(row.floors_residential, 'Residential floors', errors, {
        integer: true,
        min: 1,
      })
      if (value != null) patch.floorsResidential = value
    }
    if (!isBlank(row.total_area_residential)) {
      const value = parseNumber(row.total_area_residential, 'Residential total area', errors, {
        min: 0.01,
      })
      if (value != null) patch.totalAreaResidential = value
    }
  }

  if (existing.propertyType === 'commercial') {
    if (!isBlank(row.building_type_commercial)) {
      const value = parseAlias(
        row.building_type_commercial,
        'Commercial building type',
        commercialTypeAliases,
        errors,
      )
      if (value) patch.buildingTypeCommercial = value
    }
    if (!isBlank(row.total_area_commercial)) {
      const value = parseNumber(row.total_area_commercial, 'Commercial total area', errors, {
        min: 0.01,
      })
      if (value != null) patch.totalAreaCommercial = value
    }
    if (!isBlank(row.number_of_floors)) {
      const value = parseNumber(row.number_of_floors, 'Number of floors', errors, {
        integer: true,
        min: 1,
      })
      if (value != null) patch.numberOfFloors = value
    }
    if (!isBlank(row.units_offices)) {
      const value = parseNumber(row.units_offices, 'Units / offices', errors, {
        integer: true,
        min: 0,
      })
      if (value != null) patch.unitsOffices = value
    }
  }

  const existingInput = propertyToInput(existing) as unknown as Record<string, unknown>
  const patchRecord = patch as unknown as Record<string, unknown>
  for (const field of Object.keys(patchRecord)) {
    const before = existingInput[field]
    const after = patchRecord[field]
    const same =
      typeof before === 'object' || typeof after === 'object'
        ? JSON.stringify(before ?? null) === JSON.stringify(after ?? null)
        : before === after
    if (same) delete patchRecord[field]
  }

  const merged = { ...propertyToInput(existing), ...patch }
  const validationError = validateProperty(merged, { requirePrice: true })
  if (validationError && !errors.includes(validationError)) errors.push(validationError)

  const diffs = buildDiffs(existing, patch)
  if (!diffs.length && !errors.length) warnings.push('No changes detected in this row.')

  if (errors.length)
    return {
      ...invalidRow(
        rowNumber,
        row,
        errors,
        propertyId,
        existing.propertyName,
        existing.propertyType,
      ),
      warnings,
      input: merged,
      patch,
      diffs,
    }

  return {
    key: `${rowNumber}-${propertyId}`,
    rowNumber,
    propertyId,
    propertyName: existing.propertyName,
    propertyType: existing.propertyType,
    raw: row,
    input: merged,
    patch,
    errors: [],
    warnings,
    diffs,
    selected: diffs.length > 0,
    status: diffs.length ? 'ready' : 'skipped',
    resultPropertyId: propertyId,
    error: '',
  }
}

function isEmptyMatrixRow(row: unknown[]) {
  return row.every((cell) => isBlank(cell))
}

function canonicalizeSheet(matrix: unknown[][]) {
  const headerIndex = matrix.findIndex((row) => !isEmptyMatrixRow(row))
  if (headerIndex < 0) return { headerIndex: -1, headers: [] as string[], rows: [] }

  const rawHeaders = matrix[headerIndex] ?? []
  const headers = rawHeaders.map(normalizeHeader)
  const rows = matrix
    .slice(headerIndex + 1)
    .map((values, index) => ({ values, rowNumber: headerIndex + index + 2 }))
    .filter(({ values }) => !isEmptyMatrixRow(values))
    .map(({ values, rowNumber }) => {
      const record: Record<string, unknown> = {}
      headers.forEach((header, index) => {
        if (header) record[header] = values[index] ?? ''
      })
      return { record, rowNumber }
    })

  return { headerIndex, headers, rows }
}

export function parsePropertySheetMatrix(
  matrix: unknown[][],
  mode: PropertyDataMode,
  existingProperties: Property[] = [],
): PropertySheetResult {
  const canonical = canonicalizeSheet(matrix)
  const fileErrors: string[] = []
  const warnings: string[] = []
  const allowed = new Set<string>(mode === 'create' ? propertyCreateHeaders : propertyEditHeaders)
  const required = mode === 'create' ? createRequiredHeaders : editRequiredHeaders

  if (canonical.headerIndex < 0) {
    return { headers: [], rows: [], fileErrors: ['The selected sheet is empty.'], warnings }
  }

  const nonEmptyHeaders = canonical.headers.filter(Boolean)
  const duplicates = nonEmptyHeaders.filter(
    (header, index) => nonEmptyHeaders.indexOf(header) !== index,
  )
  if (duplicates.length)
    fileErrors.push(`Duplicate column(s): ${Array.from(new Set(duplicates)).join(', ')}.`)

  const missing = required.filter((header) => !nonEmptyHeaders.includes(header))
  if (missing.length) fileErrors.push(`Missing required column(s): ${missing.join(', ')}.`)

  const unknown = nonEmptyHeaders.filter((header) => !allowed.has(header))
  if (unknown.length)
    warnings.push(`Ignored unsupported column(s): ${Array.from(new Set(unknown)).join(', ')}.`)

  if (canonical.rows.length > PROPERTY_DATA_MAX_ROWS)
    fileErrors.push(
      `This import has ${canonical.rows.length} data rows. The maximum is ${PROPERTY_DATA_MAX_ROWS} rows per session.`,
    )

  if (fileErrors.length) return { headers: nonEmptyHeaders, rows: [], fileErrors, warnings }

  const existingById = new Map(existingProperties.map((property) => [property.id, property]))
  const rows = canonical.rows.map(({ record, rowNumber }) =>
    mode === 'create'
      ? parseCreateRow(rowNumber, record)
      : parseEditRow(rowNumber, record, existingById),
  )

  if (mode === 'edit') {
    const counts = new Map<number, number>()
    for (const row of rows) {
      if (row.propertyId == null) continue
      counts.set(row.propertyId, (counts.get(row.propertyId) ?? 0) + 1)
    }
    for (const row of rows) {
      if (row.propertyId == null || (counts.get(row.propertyId) ?? 0) < 2) continue
      row.errors = [...row.errors, `Property ID ${row.propertyId} appears more than once.`]
      row.status = 'invalid'
      row.selected = false
    }
  }

  if (mode === 'create') {
    const counts = new Map<number, number>()
    for (const row of rows) {
      if (row.input?.propertyType !== 'plot' || row.input.plotNumber == null) continue
      counts.set(row.input.plotNumber, (counts.get(row.input.plotNumber) ?? 0) + 1)
    }
    for (const row of rows) {
      const plotNumber = row.input?.propertyType === 'plot' ? row.input.plotNumber : null
      if (plotNumber == null || (counts.get(plotNumber) ?? 0) < 2) continue
      row.errors = [...row.errors, `Plot number ${plotNumber} appears more than once.`]
      row.status = 'invalid'
      row.selected = false
    }
  }

  return { headers: nonEmptyHeaders, rows, fileErrors, warnings }
}

export async function readPropertyWorkbook(file: File): Promise<PropertyWorkbookData> {
  const extension = file.name.split('.').pop()?.toLowerCase()
  if (!extension || !['csv', 'xlsx', 'xls'].includes(extension))
    throw new Error('Choose a CSV, XLSX or XLS file.')

  if (file.size > 10 * 1024 * 1024) throw new Error('The spreadsheet must be 10 MB or smaller.')

  const XLSX = await import('xlsx')
  const workbook = XLSX.read(await file.arrayBuffer(), {
    type: 'array',
    sheetRows: PROPERTY_DATA_MAX_ROWS + 2,
  })
  const sheets = workbook.SheetNames.map((name) => ({
    name,
    matrix: XLSX.utils.sheet_to_json<unknown[]>(workbook.Sheets[name], {
      header: 1,
      defval: '',
      raw: true,
      blankrows: false,
    }),
  }))

  if (!sheets.length) throw new Error('The workbook does not contain any worksheets.')
  return { filename: file.name, sheets }
}

function csvEscape(value: unknown) {
  let stringValue = stringifyCellValue(value)
  if (typeof value === 'string' && /^[\t\r ]*[=+@-]/.test(stringValue)) {
    stringValue = `'${stringValue}`
  }
  if (!/[",\r\n]/.test(stringValue)) return stringValue
  return `"${stringValue.replace(/"/g, '""')}"`
}

function rowsToCsv(headers: readonly string[], rows: Array<Record<string, unknown>>) {
  return [
    headers.map(csvEscape).join(','),
    ...rows.map((row) => headers.map((header) => csvEscape(row[header])).join(',')),
  ].join('\r\n')
}

function downloadText(filename: string, content: string, mime: string) {
  const url = URL.createObjectURL(new Blob([content], { type: mime }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

const createExampleRows: Array<Record<string, unknown>> = [
  {
    property_type: 'plot',
    property_name: 'Plot A-01',
    price: '',
    description: 'Corner plot',
    status: 'available',
    is_our_property: 'yes',
    plot_number: 1,
    plot_size: 500,
    plot_size_unit: 'sqm',
  },
  {
    property_type: 'residential',
    property_name: 'Duplex B-01',
    price: 65000000,
    description: '4 bedroom duplex',
    status: 'available',
    is_our_property: 'yes',
    building_type_residential: 'duplex',
    bedrooms: 4,
    bathrooms: 4,
    floors_residential: 2,
    total_area_residential: 320,
  },
  {
    property_type: 'commercial',
    property_name: 'Office C-01',
    price: 85000000,
    description: 'Office unit',
    status: 'available',
    is_our_property: 'yes',
    building_type_commercial: 'office',
    total_area_commercial: 450,
    number_of_floors: 2,
    units_offices: 6,
  },
]

const instructions = [
  ['Bomach Real Estate Property Data Studio'],
  ['Rule', 'Details'],
  [
    'Parsing',
    'CSV/XLS/XLSX files are parsed in the browser. The backend receives normal JSON only.',
  ],
  ['Create required', 'property_type and property_name. Type-specific fields are also validated.'],
  [
    'Edit required',
    'property_id. Download current Estate properties first for the safest edit workflow.',
  ],
  ['Blank edit cells', 'Blank means no change.'],
  ['Clear description', `Use ${PROPERTY_CLEAR_TOKEN} to clear description.`],
  [
    'Clear boundary corner',
    `Use ${PROPERTY_CLEAR_TOKEN} in both latitude and longitude cells for that corner.`,
  ],
  [
    'Commercial states',
    'Reserved and Sold cannot be created or altered through bulk data. They belong to the purchase/payment workflow.',
  ],
  ['Boundary', 'Each supplied NW/NE/SE/SW corner requires both latitude and longitude.'],
  [
    'Create price',
    'May be blank for Estate-linked properties; the Estate default price will be used.',
  ],
  ['Maximum rows', `${PROPERTY_DATA_MAX_ROWS} rows per import session.`],
]

function propertyToExportRow(property: Property): Record<string, unknown> {
  const row: Record<string, unknown> = {
    property_id: property.id,
    property_type: property.propertyType,
    property_name: property.propertyName,
    price: property.price,
    description: property.description,
    status: property.status,
    is_our_property: property.isOurProperty ? 'yes' : 'no',
    plot_number: property.plotNumber ?? '',
    plot_size: property.plotSize ?? '',
    plot_size_unit: property.plotSizeUnit ?? '',
    building_type_residential: property.buildingTypeResidential ?? '',
    bedrooms: property.bedrooms ?? '',
    bathrooms: property.bathrooms ?? '',
    floors_residential: property.floorsResidential ?? '',
    total_area_residential: property.totalAreaResidential ?? '',
    building_type_commercial: property.buildingTypeCommercial ?? '',
    total_area_commercial: property.totalAreaCommercial ?? '',
    number_of_floors: property.numberOfFloors ?? '',
    units_offices: property.unitsOffices ?? '',
  }

  for (const corner of corners) {
    row[`boundary_${corner}_lat`] = property.boundary?.[corner]?.lat ?? ''
    row[`boundary_${corner}_lng`] = property.boundary?.[corner]?.lng ?? ''
  }
  return row
}

async function downloadXlsx(
  filename: string,
  headers: readonly string[],
  rows: Array<Record<string, unknown>>,
) {
  const XLSX = await import('xlsx')
  const workbook = XLSX.utils.book_new()
  const propertyMatrix = [
    [...headers],
    ...rows.map((row) => headers.map((header) => row[header] ?? '')),
  ]
  const propertySheet = XLSX.utils.aoa_to_sheet(propertyMatrix)
  propertySheet['!cols'] = headers.map((header) => ({
    wch: Math.min(Math.max(header.length + 2, 14), 28),
  }))
  XLSX.utils.book_append_sheet(workbook, propertySheet, 'Properties')
  const instructionSheet = XLSX.utils.aoa_to_sheet(instructions)
  instructionSheet['!cols'] = [{ wch: 24 }, { wch: 90 }]
  XLSX.utils.book_append_sheet(workbook, instructionSheet, 'Instructions')
  XLSX.writeFileXLSX(workbook, filename, { compression: true })
}

export async function downloadPropertyTemplate(mode: PropertyDataMode, format: 'csv' | 'xlsx') {
  const headers = mode === 'create' ? propertyCreateHeaders : propertyEditHeaders
  const rows = mode === 'create' ? createExampleRows : []
  const stem = `bomach-property-${mode}-template`
  if (format === 'csv') {
    downloadText(`${stem}.csv`, rowsToCsv(headers, rows), 'text/csv;charset=utf-8')
    return
  }
  await downloadXlsx(`${stem}.xlsx`, headers, rows)
}

export async function downloadEstatePropertyData(
  estateName: string,
  properties: Property[],
  format: 'csv' | 'xlsx',
) {
  const rows = properties.map(propertyToExportRow)
  const safeName =
    estateName
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '') || 'estate'
  const filename = `${safeName}-properties-edit`
  if (format === 'csv') {
    downloadText(`${filename}.csv`, rowsToCsv(propertyEditHeaders, rows), 'text/csv;charset=utf-8')
    return
  }
  await downloadXlsx(`${filename}.xlsx`, propertyEditHeaders, rows)
}

export function downloadPropertyResults(
  mode: PropertyDataMode,
  rows: PropertyDataRow[],
  failedOnly: boolean,
) {
  const source = failedOnly ? rows.filter((row) => row.status === 'failed') : rows
  const dataHeaders = mode === 'create' ? propertyCreateHeaders : propertyEditHeaders
  const headers = ['__row', '__result', '__error', ...dataHeaders]
  const exportRows = source.map((row) => ({
    __row: row.rowNumber,
    __result: row.status,
    __error: row.error || row.errors.join(' | '),
    ...row.raw,
  }))
  downloadText(
    `bomach-property-${mode}-${failedOnly ? 'failed' : 'results'}.csv`,
    rowsToCsv(headers, exportRows),
    'text/csv;charset=utf-8',
  )
}
