import { authHandlers } from './auth.handlers'
import { dashboardHandlers } from '@/modules/dashboard/mocks/dashboard.handlers'
import { healthHandlers } from './health.handlers'

export const handlers = [...authHandlers, ...dashboardHandlers, ...healthHandlers]
