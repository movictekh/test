import { queryOptions } from '@tanstack/react-query'

import { authApi } from './auth.api'
import { authKeys } from './auth.keys'

export const authQueries = {
  currentUser: () =>
    queryOptions({
      queryKey: authKeys.currentUser(),
      queryFn: () => authApi.currentUser(),
      staleTime: 60_000,
      retry: false,
    }),
}
