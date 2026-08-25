import { queryOptions } from '@tanstack/react-query'
import { realEstateApi } from './real-estate.api'
import { realEstateKeys } from './real-estate.keys'
import type { BrokerageFilters, EstateFilters, PropertyFilters } from './real-estate.types'
export const realEstateQueries = {
  estates: (f: EstateFilters) =>
    queryOptions({
      queryKey: realEstateKeys.estateList(f),
      queryFn: () => realEstateApi.listEstates(f),
      placeholderData: (p) => p,
      staleTime: 15_000,
    }),
  detail: (id: number) =>
    queryOptions({
      queryKey: realEstateKeys.estateDetail(id),
      queryFn: () => realEstateApi.estateDetail(id),
      staleTime: 15_000,
    }),
  stats: (id: number) =>
    queryOptions({
      queryKey: realEstateKeys.estateStats(id),
      queryFn: () => realEstateApi.estateStats(id),
      staleTime: 10_000,
    }),
  layout: (id: number) =>
    queryOptions({
      queryKey: realEstateKeys.estateLayout(id),
      queryFn: () => realEstateApi.estateLayout(id),
      staleTime: 10_000,
    }),
  choices: () =>
    queryOptions({
      queryKey: realEstateKeys.estateChoices(),
      queryFn: realEstateApi.estateChoices,
      staleTime: 60_000,
    }),
  properties: (estateId: number, f: PropertyFilters) =>
    queryOptions({
      queryKey: realEstateKeys.propertyList(estateId, f),
      queryFn: () => realEstateApi.listProperties(estateId, f),
      placeholderData: (p) => p,
      staleTime: 10_000,
    }),
  standaloneProperties: (f: PropertyFilters) =>
    queryOptions({
      queryKey: realEstateKeys.standalonePropertyList(f),
      queryFn: () => realEstateApi.listStandaloneProperties(f),
      placeholderData: (p) => p,
      staleTime: 10_000,
    }),
  brokerage: (f: BrokerageFilters) =>
    queryOptions({
      queryKey: realEstateKeys.brokerageList(f),
      queryFn: () => realEstateApi.listBrokerage(f),
      placeholderData: (p) => p,
      staleTime: 10_000,
    }),
  brokerageStats: () =>
    queryOptions({
      queryKey: realEstateKeys.brokerageStats(),
      queryFn: realEstateApi.brokerageStats,
      staleTime: 10_000,
    }),
}
