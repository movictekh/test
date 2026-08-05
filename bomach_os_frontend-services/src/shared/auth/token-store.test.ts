import { beforeEach, describe, expect, it, vi } from 'vitest'

import { tokenStore } from './token-store'

describe('tokenStore', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
    window.localStorage.clear()
  })

  it('stores access in sessionStorage and refresh in localStorage', () => {
    tokenStore.set({
      accessToken: 'access-token',
      refreshToken: 'refresh-token',
    })

    expect(window.sessionStorage.getItem('bomach-access-token')).toBe('access-token')
    expect(window.localStorage.getItem('bomach-refresh-token')).toBe('refresh-token')
    expect(window.localStorage.getItem('bomach-access-token')).toBeNull()
    expect(window.sessionStorage.getItem('bomach-refresh-token')).toBeNull()
  })

  it('updates only the access token', () => {
    tokenStore.set({
      accessToken: 'first-access-token',
      refreshToken: 'refresh-token',
    })

    tokenStore.updateAccessToken('second-access-token')

    expect(tokenStore.get()).toEqual({
      accessToken: 'second-access-token',
      refreshToken: 'refresh-token',
    })
  })

  it('publishes the session-end reason', () => {
    const listener = vi.fn()
    const unsubscribe = tokenStore.subscribe(listener)

    tokenStore.set({
      accessToken: 'access-token',
      refreshToken: 'refresh-token',
    })
    tokenStore.clear('expired')

    expect(tokenStore.get()).toBeNull()
    expect(listener).toHaveBeenLastCalledWith({
      tokens: null,
      reason: 'expired',
    })

    unsubscribe()
  })
})
