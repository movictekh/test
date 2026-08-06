import { serviceAdministrationHandlers } from '@/modules/service-administration/mocks/service-administration.handlers'
import { authHandlers } from './auth.handlers'
import { dashboardHandlers } from '@/modules/dashboard/mocks/dashboard.handlers'
import { healthHandlers } from './health.handlers'

export const handlers = [
  ...serviceAdministrationHandlers,
  ...authHandlers,
  ...dashboardHandlers,
  ...healthHandlers,
]
