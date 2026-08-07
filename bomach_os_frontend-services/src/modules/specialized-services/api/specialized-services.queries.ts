import { queryOptions } from '@tanstack/react-query'
import { specializedServicesApi } from './specialized-services.api'
import { specializedServicesKeys } from './specialized-services.keys'
export const specializedServicesQueries = {
  workspace: () =>
    queryOptions({
      queryKey: specializedServicesKeys.workspace(),
      queryFn: () => specializedServicesApi.getWorkspace(),
      staleTime: 30_000,
    }),
}
