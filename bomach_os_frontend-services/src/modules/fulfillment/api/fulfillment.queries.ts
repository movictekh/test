import { queryOptions } from '@tanstack/react-query'

import { fulfillmentApi } from './fulfillment.api'
import { fulfillmentKeys } from './fulfillment.keys'

export const fulfillmentQueries = {
  workspace: () =>
    queryOptions({
      queryKey: fulfillmentKeys.workspace(),
      queryFn: () => fulfillmentApi.getWorkspace(),
      staleTime: 30_000,
    }),
}
