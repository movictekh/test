import { describe, expect, it } from 'vitest'

import type { AuthUser } from '@/app/auth'
import { PERMISSIONS } from '@/app/permissions'

import { getServiceAdministrationCapabilities } from './service-administration.permissions'

function user(permissions: AuthUser['permissions']): AuthUser {
  return {
    id: 'staff-1',
    name: 'Staff',
    email: 'staff@bomach.local',
    username: 'staff',
    initials: 'ST',
    role: 'UNKNOWN',
    roleLabel: 'Backend Role',
    kind: 'staff',
    permissions,
    backendPermissions: [...permissions],
    isVerified: true,
  }
}

describe('Service Administration capabilities', () => {
  it('keeps list and view independent', () => {
    const capabilities = getServiceAdministrationCapabilities(user([PERMISSIONS.servicesList]))

    expect(capabilities.canListServices).toBe(true)
    expect(capabilities.canViewService).toBe(false)
    expect(capabilities.canCreateService).toBe(false)
    expect(capabilities.canUpdateService).toBe(false)
  })

  it('supports a genuine read-only catalogue user', () => {
    const capabilities = getServiceAdministrationCapabilities(
      user([PERMISSIONS.servicesList, PERMISSIONS.servicesView]),
    )

    expect(capabilities.canListServices).toBe(true)
    expect(capabilities.canViewService).toBe(true)
    expect(capabilities.canCreateService).toBe(false)
  })

  it('keeps request-form, workflow and branch writes independent', () => {
    const capabilities = getServiceAdministrationCapabilities(
      user([
        PERMISSIONS.serviceRequestFormsList,
        PERMISSIONS.serviceWorkflowsList,
        PERMISSIONS.serviceBranchActivationsList,
        PERMISSIONS.serviceWorkflowsUpdate,
      ]),
    )

    expect(capabilities.canUpdateRequestForm).toBe(false)
    expect(capabilities.canUpdateWorkflow).toBe(true)
    expect(capabilities.canUpdateBranchActivations).toBe(false)
  })

  it('matches publish permission to the backend services.update endpoint', () => {
    const capabilities = getServiceAdministrationCapabilities(user([PERMISSIONS.servicesUpdate]))

    expect(capabilities.canPublishService).toBe(true)
  })

  it('keeps pricing list and detail permissions independent', () => {
    const listOnly = getServiceAdministrationCapabilities(
      user([PERMISSIONS.servicePricingConfigsList]),
    )
    const listAndView = getServiceAdministrationCapabilities(
      user([PERMISSIONS.servicePricingConfigsList, PERMISSIONS.servicePricingConfigsView]),
    )

    expect(listOnly.canListPricingConfigs).toBe(true)
    expect(listOnly.canViewPricingConfig).toBe(false)
    expect(listAndView.canViewPricingConfig).toBe(true)
  })

  it('allows the wizard to start with only core create authority', () => {
    const capabilities = getServiceAdministrationCapabilities(
      user([PERMISSIONS.servicesCreate, PERMISSIONS.categoriesList]),
    )
    expect(capabilities.canCreateInitialServiceSetup).toBe(true)
    expect(capabilities.canUpdateSubservices).toBe(false)
    expect(capabilities.canCreatePricingConfig).toBe(false)
    expect(capabilities.canCreateRequestForm).toBe(false)
    expect(capabilities.canCreateWorkflow).toBe(false)
  })

  it('keeps optional create-wizard stages permission-independent', () => {
    const capabilities = getServiceAdministrationCapabilities(
      user([
        PERMISSIONS.servicesCreate,
        PERMISSIONS.categoriesList,
        PERMISSIONS.servicePricingConfigsCreate,
        PERMISSIONS.serviceWorkflowsCreate,
      ]),
    )
    expect(capabilities.canCreateInitialServiceSetup).toBe(true)
    expect(capabilities.canCreatePricingConfig).toBe(true)
    expect(capabilities.canCreateWorkflow).toBe(true)
    expect(capabilities.canCreateRequestForm).toBe(false)
    expect(capabilities.canUpdateBranchActivations).toBe(false)
  })
})
