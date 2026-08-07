import { queryOptions } from '@tanstack/react-query'

import { experienceIntelligenceApi } from './experience-intelligence.api'
import { experienceIntelligenceKeys } from './experience-intelligence.keys'

export const experienceIntelligenceQueries = {
  workspace: () =>
    queryOptions({
      queryKey: experienceIntelligenceKeys.workspace(),
      queryFn: () => experienceIntelligenceApi.getWorkspace(),
      staleTime: 30_000,
    }),
}
