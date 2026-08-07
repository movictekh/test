import { apiClient } from '@/shared/api/api-client'
import { MOCK_API_PREFIX } from '@/mocks/mock-api'
import type {
  CreateBrokeragePropertyInput,
  CreateEstateInput,
  SpecializedWorkspace,
  UpdatePlotInput,
} from '../types/specialized-services.types'
export const specializedServicesApi = {
  getWorkspace: () =>
    apiClient.get<SpecializedWorkspace>(`${MOCK_API_PREFIX}/specialized-services`),
  createEstate: (input: CreateEstateInput) =>
    apiClient.post<SpecializedWorkspace>(`${MOCK_API_PREFIX}/specialized-services/estates`, input),
  updatePlot: (input: UpdatePlotInput) =>
    apiClient.patch<SpecializedWorkspace>(
      `${MOCK_API_PREFIX}/specialized-services/estates/${input.estateId}/plots/${input.plotNo}`,
      input,
    ),
  createBrokerageProperty: (input: CreateBrokeragePropertyInput) =>
    apiClient.post<SpecializedWorkspace>(
      `${MOCK_API_PREFIX}/specialized-services/brokerage`,
      input,
    ),
}
