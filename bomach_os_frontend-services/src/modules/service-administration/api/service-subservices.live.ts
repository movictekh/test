import { serviceAdministrationBackendApi } from './service-administration.backend-api'

import type { ServiceSubserviceSetup } from '../types/service-administration.types'

function slug(value: string): string {
  return value
    .toLowerCase()
    .replace(/&/g, ' and ')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '')
}

function subserviceCode(name: string, code?: string | null): string {
  const explicit = code?.trim()
  if (explicit) {
    return explicit
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
  }
  return slug(name).replace(/_/g, '-')
}

export async function syncLiveSubservices(
  serviceId: number,
  subservices: ServiceSubserviceSetup[],
) {
  const existing = await serviceAdministrationBackendApi.listSubservices(serviceId)
  const existingByCode = new Map(
    existing.map((item) => [subserviceCode(item.name, item.code), item] as const),
  )
  const desiredCodes = new Set<string>()

  for (const [index, item] of subservices.entries()) {
    const effectiveCode = subserviceCode(item.name, item.code)
    desiredCodes.add(effectiveCode)

    const payload = {
      ...(item.code?.trim() ? { code: item.code.trim() } : {}),
      name: item.name.trim(),
      description: item.description.trim(),
      status: item.status,
      default_sla_days: item.defaultSlaDays,
      sort_order: index,
    }

    const existingItem = existingByCode.get(effectiveCode)
    if (existingItem) {
      await serviceAdministrationBackendApi.updateSubservice(serviceId, existingItem.id, payload)
      continue
    }

    await serviceAdministrationBackendApi.createSubservice(serviceId, payload)
  }

  for (const item of existing) {
    const effectiveCode = subserviceCode(item.name, item.code)
    if (desiredCodes.has(effectiveCode)) continue
    await serviceAdministrationBackendApi.deleteSubservice(serviceId, item.id)
  }
}
