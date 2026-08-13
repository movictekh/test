import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { tokenStore } from '@/shared/auth/token-store'

import { authApi } from './auth.api'

describe('authApi', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
    window.localStorage.clear()
  })

  afterEach(() => {
    tokenStore.clear('manual')
  })

  it('logs in and loads the mock staff user', async () => {
    const result = await authApi.login({
      email: 'service.admin@bomach.local',
      password: 'demo-password',
    })

    expect(result.type).toBe('authenticated')
    expect(tokenStore.getAccessToken()).toContain('mock-access-service-administrator')
    expect(tokenStore.getRefreshToken()).toContain('mock-refresh-service-administrator')

    const user = await authApi.currentUser()

    expect(user).toMatchObject({
      email: 'service.admin@bomach.local',
      kind: 'staff',
      role: 'SERVICE_ADMINISTRATOR',
    })
  })

  it('restores the staff session when only the refresh token survives', async () => {
    const result = await authApi.login({
      email: 'service.admin@bomach.local',
      password: 'demo-password',
    })

    expect(result.type).toBe('authenticated')
    expect(tokenStore.getRefreshToken()).toContain('mock-refresh-service-administrator')

    window.sessionStorage.clear()

    expect(tokenStore.getAccessToken()).toBeNull()
    expect(tokenStore.hasRefreshToken()).toBe(true)

    const user = await authApi.currentUser()

    expect(tokenStore.getAccessToken()).toContain('mock-access-service-administrator-refreshed')
    expect(user).toMatchObject({
      email: 'service.admin@bomach.local',
      kind: 'staff',
      role: 'SERVICE_ADMINISTRATOR',
    })
  })

  it('rejects invalid credentials without emitting a session-expired event', async () => {
    const sessionEvents: Array<{ reason?: string }> = []
    const unsubscribe = tokenStore.subscribe((event) => {
      sessionEvents.push({ ...(event.reason ? { reason: event.reason } : {}) })
    })

    try {
      await expect(
        authApi.login({
          email: 'service.admin@bomach.local',
          password: 'wrong-password',
        }),
      ).rejects.toThrow('No active account found with the given credentials.')

      expect(sessionEvents).toEqual([])
    } finally {
      unsubscribe()
    }
  })

  it('returns null when there is no stored session', async () => {
    expect(await authApi.currentUser()).toBeNull()
  })
})
