import { useCallback, useEffect, useMemo, useState, type PropsWithChildren } from 'react'
import { z } from 'zod'

import { AuthContext } from './auth.context'
import {
  APP_ROLES,
  AUTH_USER_KINDS,
  type AuthContextValue,
  type AuthUser,
  type MockAuthProfile,
} from './auth.types'

const AUTH_STORAGE_KEY = 'bomach-ui-auth-session'

const authUserSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  email: z.string().email(),
  initials: z.string().min(1).max(4),
  role: z.enum(APP_ROLES),
  kind: z.enum(AUTH_USER_KINDS),
})

const mockUsers = {
  'service-administrator': {
    id: 'usr-service-admin',
    name: 'Kene Eze',
    email: 'service.admin@bomach.local',
    initials: 'KE',
    role: 'SERVICE_ADMINISTRATOR',
    kind: 'staff',
  },
  client: {
    id: 'usr-client-demo',
    name: 'Chief Okafor',
    email: 'client@bomach.local',
    initials: 'CO',
    role: 'CLIENT',
    kind: 'client',
  },
} satisfies Record<MockAuthProfile, AuthUser>

function readStoredUser(): AuthUser | null {
  if (typeof window === 'undefined') {
    return null
  }

  const storedValue = window.localStorage.getItem(AUTH_STORAGE_KEY)

  if (!storedValue) {
    return null
  }

  try {
    const parsedValue: unknown = JSON.parse(storedValue)
    const result = authUserSchema.safeParse(parsedValue)

    return result.success ? result.data : null
  } catch {
    return null
  }
}

function persistUser(user: AuthUser | null): void {
  if (typeof window === 'undefined') {
    return
  }

  if (user) {
    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user))
    return
  }

  window.localStorage.removeItem(AUTH_STORAGE_KEY)
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<AuthUser | null>(() => readStoredUser())

  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      if (event.key === AUTH_STORAGE_KEY) {
        setUser(readStoredUser())
      }
    }

    window.addEventListener('storage', handleStorage)

    return () => {
      window.removeEventListener('storage', handleStorage)
    }
  }, [])

  const signInAsProfile = useCallback((profile: MockAuthProfile): Promise<AuthUser> => {
    const nextUser = mockUsers[profile]

    persistUser(nextUser)
    setUser(nextUser)

    return Promise.resolve(nextUser)
  }, [])

  const signOut = useCallback((): Promise<void> => {
    persistUser(null)
    setUser(null)

    return Promise.resolve()
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading: false,
      signInAsProfile,
      signOut,
    }),
    [signInAsProfile, signOut, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
