import { z } from 'zod'

const TOKEN_STORAGE_KEY = 'bomach-auth-tokens'

const tokenPairSchema = z.object({
  accessToken: z.string().min(1),
  refreshToken: z.string().min(1),
})

export type AuthTokenPair = z.infer<typeof tokenPairSchema>

type TokenListener = (tokens: AuthTokenPair | null) => void

const listeners = new Set<TokenListener>()
let memoryTokens: AuthTokenPair | null = null

function readPersistedTokens(): AuthTokenPair | null {
  if (typeof window === 'undefined') return null

  const value = window.localStorage.getItem(TOKEN_STORAGE_KEY)
  if (!value) return null

  try {
    const result = tokenPairSchema.safeParse(JSON.parse(value) as unknown)
    return result.success ? result.data : null
  } catch {
    return null
  }
}

function notify(tokens: AuthTokenPair | null): void {
  listeners.forEach((listener) => listener(tokens))
}

export const tokenStore = {
  get(): AuthTokenPair | null {
    if (memoryTokens) return memoryTokens
    memoryTokens = readPersistedTokens()
    return memoryTokens
  },

  set(tokens: AuthTokenPair): void {
    memoryTokens = tokens

    if (typeof window !== 'undefined') {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens))
    }

    notify(tokens)
  },

  updateAccessToken(accessToken: string): void {
    const current = tokenStore.get()
    if (!current) return

    tokenStore.set({
      ...current,
      accessToken,
    })
  },

  clear(): void {
    memoryTokens = null

    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY)
    }

    notify(null)
  },

  subscribe(listener: TokenListener): () => void {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
}
