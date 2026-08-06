import { queryOptions } from '@tanstack/react-query'

import { commercialApi } from './commercial.api'
import { commercialKeys } from './commercial.keys'

export const commercialQueries = {
  workspace: () =>
    queryOptions({
      queryKey: commercialKeys.workspace(),
      queryFn: () => commercialApi.getWorkspace(),
      staleTime: 30_000,
    }),
}
