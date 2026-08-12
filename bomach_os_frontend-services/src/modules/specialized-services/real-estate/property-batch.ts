import type { CreatePropertyInput, PropertyBatchItem } from './real-estate.types'
export function buildPropertyBatch(
  template: CreatePropertyInput,
  count: number,
  startNumber: number,
  namePrefix: string,
): PropertyBatchItem[] {
  return Array.from({ length: count }, (_, index) => {
    const sequence = startNumber + index
    const name =
      template.propertyType === 'plot'
        ? `${namePrefix || 'Plot'} ${String(sequence).padStart(2, '0')}`
        : count === 1
          ? template.propertyName
          : `${namePrefix || template.propertyName} ${sequence}`
    return {
      key: `${Date.now()}-${sequence}-${index}`,
      sequence,
      input: {
        ...template,
        propertyName: name,
        ...(template.propertyType === 'plot' ? { plotNumber: sequence } : {}),
      },
      status: 'queued',
      propertyId: null,
      error: '',
    }
  })
}
