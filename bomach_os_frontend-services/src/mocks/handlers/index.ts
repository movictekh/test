import { commercialHandlers } from '@/modules/commercial/mocks/commercial.handlers'
import { fulfillmentHandlers } from '@/modules/fulfillment/mocks/fulfillment.handlers'
import { specializedServicesHandlers } from '@/modules/specialized-services/mocks/specialized-services.handlers'
import { serviceAdministrationHandlers } from '@/modules/service-administration/mocks/service-administration.handlers'
import { authHandlers } from './auth.handlers'
import { dashboardHandlers } from '@/modules/dashboard/mocks/dashboard.handlers'
import { healthHandlers } from './health.handlers'

export const handlers = [
  ...commercialHandlers,
  ...fulfillmentHandlers,
  ...specializedServicesHandlers,
  ...serviceAdministrationHandlers,
  ...authHandlers,
  ...dashboardHandlers,
  ...healthHandlers,
]
