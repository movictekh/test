import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { tokenStore } from '@/shared/auth/token-store'

import { authApi } from './auth.api'

describe('auth role bootstrap access', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
    window.localStorage.clear()
    tokenStore.set({
      accessToken: 'access-token',
      refreshToken: 'refresh-token',
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    tokenStore.clear('manual')
  })

  it('surfaces a role access error when self role bootstrap returns 403', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')

    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: 77,
            email: 'service.admin@bomach.local',
            username: 'service.admin',
            first_name: 'Service',
            last_name: 'Administrator',
            phone_number: null,
            is_verified: true,
            created_at: '2026-08-08T00:00:00Z',
          }),
          {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            detail: 'You do not have permission to perform this action.',
          }),
          {
            status: 403,
            headers: { 'Content-Type': 'application/json' },
          },
        ),
      )

    await expect(authApi.currentUser()).rejects.toMatchObject({
      name: 'AuthAccessError',
      issue: 'role-access-denied',
    })
  })
})
