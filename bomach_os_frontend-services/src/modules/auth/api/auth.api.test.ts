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

  it('detects the mock client profile', async () => {
    await authApi.login({
      email: 'client@bomach.local',
      password: 'demo-password',
    })

    const user = await authApi.currentUser()

    expect(user).toMatchObject({
      email: 'client@bomach.local',
      kind: 'client',
      role: 'CLIENT',
    })
  })

  it('rejects invalid credentials', async () => {
    await expect(
      authApi.login({
        email: 'service.admin@bomach.local',
        password: 'wrong-password',
      }),
    ).rejects.toThrow('No active account found with the given credentials.')
  })

  it('returns null when there is no stored session', async () => {
    expect(await authApi.currentUser()).toBeNull()
  })
})
