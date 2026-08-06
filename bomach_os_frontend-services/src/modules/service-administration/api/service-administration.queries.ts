import { queryOptions } from '@tanstack/react-query'

import { serviceAdministrationApi } from './service-administration.api'
import { serviceAdministrationKeys } from './service-administration.keys'

export const serviceAdministrationQueries = {
  workspace: () =>
    queryOptions({
      queryKey: serviceAdministrationKeys.workspace(),
      queryFn: () => serviceAdministrationApi.getWorkspace(),
      staleTime: 30_000,
    }),
}
