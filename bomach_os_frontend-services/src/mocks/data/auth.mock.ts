import type { RoleResponseDto, UserResponseDto } from '@/modules/auth/types/auth.contracts'

export const mockAuthUsers = {
  'service-administrator': {
    user: {
      id: 101,
      email: 'service.admin@bomach.local',
      username: 'service.admin',
      first_name: 'Kene',
      last_name: 'Eze',
      phone_number: null,
      is_verified: true,
      created_at: '2026-08-01T08:00:00Z',
    } satisfies UserResponseDto,
    role: {
      id: 1,
      name: 'Service Administrator',
      branches: [],
      permissions: {
        dashboard: ['read'],
        service: ['read', 'create', 'update'],
        request: ['read', 'create', 'update'],
        quote: ['read', 'create'],
        approval: ['read'],
        order: ['read'],
        task: ['read'],
        deliverable: ['read'],
        report: ['read'],
        audit: ['read'],
      },
      created_at: '2026-08-01T08:00:00Z',
      updated_at: '2026-08-01T08:00:00Z',
    } satisfies RoleResponseDto,
  },
  client: {
    user: {
      id: 202,
      email: 'client@bomach.local',
      username: 'chief.okafor',
      first_name: 'Chief',
      last_name: 'Okafor',
      phone_number: null,
      is_verified: true,
      created_at: '2026-08-01T08:00:00Z',
    } satisfies UserResponseDto,
  },
} as const
