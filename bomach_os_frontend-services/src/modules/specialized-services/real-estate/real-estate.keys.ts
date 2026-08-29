import type { BrokerageFilters, EstateFilters, PropertyFilters } from './real-estate.types'
export const realEstateKeys = {
  all: ['specialized-services', 'real-estate'] as const,
  estates: () => [...realEstateKeys.all, 'estates'] as const,
  estateList: (f: EstateFilters) => [...realEstateKeys.estates(), 'list', f] as const,
  estateDetail: (id: number) => [...realEstateKeys.estates(), 'detail', id] as const,
  estateStats: (id: number) => [...realEstateKeys.estates(), 'stats', id] as const,
  estateLayout: (id: number) => [...realEstateKeys.estates(), 'layout', id] as const,
  estateChoices: () => [...realEstateKeys.estates(), 'choices'] as const,
  properties: (estateId: number) => [...realEstateKeys.all, 'properties', estateId] as const,
  propertyList: (estateId: number, f: PropertyFilters) =>
    [...realEstateKeys.properties(estateId), 'list', f] as const,
  propertyDetail: (estateId: number, id: number) =>
    [...realEstateKeys.properties(estateId), 'detail', id] as const,
  brokerage: () => [...realEstateKeys.all, 'brokerage'] as const,
  brokerageList: (f: BrokerageFilters) => [...realEstateKeys.brokerage(), 'list', f] as const,
  brokerageStats: () => [...realEstateKeys.brokerage(), 'stats'] as const,
}
