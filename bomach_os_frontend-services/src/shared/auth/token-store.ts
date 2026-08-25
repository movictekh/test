import { z } from 'zod'

const ACCESS_TOKEN_KEY = 'bomach-access-token'
const REFRESH_TOKEN_KEY = 'bomach-refresh-token'

const tokenSchema = z.string().min(1)

export type AuthSessionEndReason = 'logout' | 'expired' | 'invalid' | 'storage-cleared' | 'manual'

export interface AuthTokenPair {
  accessToken: string
  refreshToken: string
}

export interface AuthSessionEvent {
  tokens: AuthTokenPair | null
  reason?: AuthSessionEndReason
}

type TokenListener = (event: AuthSessionEvent) => void
const listeners = new Set<TokenListener>()

function notify(event: AuthSessionEvent): void {
  listeners.forEach((listener) => listener(event))
}

function readSessionValue(key: string): string | null {
  if (typeof window === 'undefined') return null
  const result = tokenSchema.safeParse(window.sessionStorage.getItem(key))
  if (result.success) return result.data

  // Fallback to localStorage if not in sessionStorage
  const localResult = tokenSchema.safeParse(window.localStorage.getItem(key))
  return localResult.success ? localResult.data : null
}

function readLocalValue(key: string): string | null {
  if (typeof window === 'undefined') return null
  const result = tokenSchema.safeParse(window.localStorage.getItem(key))
  return result.success ? result.data : null
}

// Ingest tokens from URL parameters synchronously upon script evaluation
if (typeof window !== 'undefined') {
  try {
    const params = new URLSearchParams(window.location.search)
    const urlToken = params.get('token') || params.get('access_token')
    const urlRefreshToken = params.get('refresh_token') || urlToken
    if (urlToken) {
      window.sessionStorage.setItem(ACCESS_TOKEN_KEY, urlToken)
      window.localStorage.setItem(ACCESS_TOKEN_KEY, urlToken)
      if (urlRefreshToken) {
        window.sessionStorage.setItem(REFRESH_TOKEN_KEY, urlRefreshToken)
        window.localStorage.setItem(REFRESH_TOKEN_KEY, urlRefreshToken)
      }
    }
  } catch {
    // Ignore malformed URL/search parsing during bootstrap.
  }
}

export const tokenStore = {
  get(): AuthTokenPair | null {
    const accessToken = readSessionValue(ACCESS_TOKEN_KEY)
    const refreshToken = readLocalValue(REFRESH_TOKEN_KEY)
    return accessToken && refreshToken ? { accessToken, refreshToken } : null
  },

  getAccessToken(): string | null {
    return readSessionValue(ACCESS_TOKEN_KEY)
  },

  getRefreshToken(): string | null {
    return readLocalValue(REFRESH_TOKEN_KEY)
  },

  hasRefreshToken(): boolean {
    return Boolean(readLocalValue(REFRESH_TOKEN_KEY))
  },

  set(tokens: AuthTokenPair): void {
    if (typeof window === 'undefined') return
    window.sessionStorage.setItem(ACCESS_TOKEN_KEY, tokens.accessToken)
    window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken)
    notify({ tokens })
  },

  updateAccessToken(accessToken: string): void {
    if (typeof window === 'undefined') return
    window.sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken)

    const refreshToken = readLocalValue(REFRESH_TOKEN_KEY)
    if (refreshToken) notify({ tokens: { accessToken, refreshToken } })
  },

  clear(reason: AuthSessionEndReason = 'manual'): void {
    if (typeof window !== 'undefined') {
      window.sessionStorage.removeItem(ACCESS_TOKEN_KEY)
      window.localStorage.removeItem(REFRESH_TOKEN_KEY)
    }
    notify({ tokens: null, reason })
  },

  subscribe(listener: TokenListener): () => void {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },

  syncFromStorage(): void {
    const tokens = tokenStore.get()
    notify({
      tokens,
      ...(tokens ? {} : { reason: 'storage-cleared' as const }),
    })
  },
}
