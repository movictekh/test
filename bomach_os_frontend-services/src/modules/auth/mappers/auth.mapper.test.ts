import { describe, expect, it } from 'vitest'

import { PERMISSIONS } from '@/app/permissions'

import type { RoleResponseDto, UserResponseDto } from '../types/auth.contracts'
import { mapAuthenticatedUser } from './auth.mapper'

const user: UserResponseDto = {
  id: 7,
  email: 'staff@bomach.local',
  username: 'staff.user',
  first_name: 'Staff',
  last_name: 'User',
  phone_number: null,
  is_verified: true,
  created_at: '2026-08-07T00:00:00Z',
}

function role(name: string, permissions: RoleResponseDto['permissions']): RoleResponseDto {
  return {
    id: 1,
    name,
    branches: [],
    permissions,
    created_at: '2026-08-07T00:00:00Z',
    updated_at: '2026-08-07T00:00:00Z',
  }
}

describe('mapAuthenticatedUser', () => {
  it('maps an empty backend permission payload to zero frontend permissions', () => {
    const mapped = mapAuthenticatedUser(user, role('Service Administrator', {}))

    expect(mapped.permissions).toEqual([])
  })

  it('maps only supported backend capabilities', () => {
    const mapped = mapAuthenticatedUser(
      user,
      role('Service Manager', {
        orders: ['view', 'list'],
        service_requests: ['view', 'list', 'create'],
        unsupported_resource: ['read'],
      }),
    )

    expect(mapped.permissions).toEqual([
      PERMISSIONS.ordersList,
      PERMISSIONS.serviceRequestsList,
      PERMISSIONS.serviceRequestsCreate,
    ])

    expect(mapped.backendPermissions).toContain('unsupported_resource.read')
  })

  it('does not convert an unknown backend role into a privileged frontend role', () => {
    const mapped = mapAuthenticatedUser(
      user,
      role('Regional Operations Supervisor', {
        order: ['read'],
      }),
    )

    expect(mapped.role).toBe('UNKNOWN')
    expect(mapped.roleLabel).toBe('Regional Operations Supervisor')
    expect(mapped.permissions).toEqual([PERMISSIONS.ordersList])
  })
})
