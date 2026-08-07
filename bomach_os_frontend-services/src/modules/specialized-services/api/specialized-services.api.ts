import { apiClient } from '@/shared/api/api-client'
import type {
  CreateBrokeragePropertyInput,
  CreateEstateInput,
  SpecializedWorkspace,
  UpdatePlotInput,
} from '../types/specialized-services.types'
export const specializedServicesApi = {
  getWorkspace: () => apiClient.get<SpecializedWorkspace>('/ui-prototype/specialized-services'),
  createEstate: (input: CreateEstateInput) =>
    apiClient.post<SpecializedWorkspace>('/ui-prototype/specialized-services/estates', input),
  updatePlot: (input: UpdatePlotInput) =>
    apiClient.patch<SpecializedWorkspace>(
      `/ui-prototype/specialized-services/estates/${input.estateId}/plots/${input.plotNo}`,
      input,
    ),
  createBrokerageProperty: (input: CreateBrokeragePropertyInput) =>
    apiClient.post<SpecializedWorkspace>('/ui-prototype/specialized-services/brokerage', input),
}
