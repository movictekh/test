import { authHandlers } from './auth.handlers'
import { healthHandlers } from './health.handlers'

export const handlers = [...authHandlers, ...healthHandlers]
