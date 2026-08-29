import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, type PropsWithChildren } from 'react'

import { authMutations } from '@/modules/auth/api/auth.mutations'
import { authQueries } from '@/modules/auth/api/auth.queries'
import { isAuthAccessError } from '@/modules/auth/errors/auth-access-error'
import type { LoginCredentials, LoginResult } from '@/modules/auth/types/auth.types'
import { redirectToSessionExpiredLogin } from '@/shared/auth/session-navigation'
import { tokenStore } from '@/shared/auth/token-store'
import { useToast } from '@/shared/ui'

import { AuthContext } from './auth.context'
import type { AuthContextValue, AuthUser } from './auth.types'

export function AuthProvider({ children }: PropsWithChildren) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const currentUserQueryOptions = useMemo(() => authQueries.currentUser(), [])
  const currentUserQuery = useQuery(currentUserQueryOptions)
  const { mutateAsync: loginMutateAsync } = useMutation(authMutations.login())
  const { mutateAsync: verifyTwoFactorMutateAsync } = useMutation(authMutations.verifyTwoFactor())
  const { mutateAsync: logoutMutateAsync } = useMutation(authMutations.logout())

  useEffect(() => {
    const unsubscribe = tokenStore.subscribe(({ tokens, reason }) => {
      if (tokens) return

      queryClient.setQueryData(currentUserQueryOptions.queryKey, null)

      if (reason === 'expired' || reason === 'invalid' || reason === 'storage-cleared') {
        queryClient.clear()
        redirectToSessionExpiredLogin()
      }
    })

    const handleStorage = (event: StorageEvent) => {
      if (event.storageArea === window.localStorage) tokenStore.syncFromStorage()
    }

    window.addEventListener('storage', handleStorage)

    return () => {
      unsubscribe()
      window.removeEventListener('storage', handleStorage)
    }
  }, [currentUserQueryOptions.queryKey, queryClient])

  // Handle token passed from query params (e.g. embedded in Bomach OS) or window postMessage
  useEffect(() => {
    if (typeof window === 'undefined') return

    const params = new URLSearchParams(window.location.search)
    const queryToken = params.get('token') || params.get('access_token')
    const queryRefreshToken = params.get('refresh_token') || queryToken

    if (queryToken) {
      tokenStore.set({
        accessToken: queryToken,
        refreshToken: queryRefreshToken || queryToken,
      })
      queryClient.invalidateQueries({
        queryKey: currentUserQueryOptions.queryKey,
      })
    }

    const handleMessage = (e: MessageEvent) => {
      if (e.data && e.data.type === 'BOMACH_AUTH_TOKEN' && e.data.token) {
        const t = String(e.data.token)
        tokenStore.set({
          accessToken: t,
          refreshToken: e.data.refreshToken ? String(e.data.refreshToken) : t,
        })
        queryClient.invalidateQueries({
          queryKey: currentUserQueryOptions.queryKey,
        })
      }
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [currentUserQueryOptions.queryKey, queryClient])

  const loadCurrentUser = useCallback(async (): Promise<AuthUser> => {
    const user = await queryClient.fetchQuery({
      ...currentUserQueryOptions,
      staleTime: 0,
    })

    if (!user) throw new Error('The authenticated user could not be loaded.')
    return user
  }, [currentUserQueryOptions, queryClient])

  const login = useCallback(
    async (credentials: LoginCredentials): Promise<LoginResult> => {
      const result = await loginMutateAsync(credentials)

      if (result.type === 'authenticated') {
        try {
          await queryClient.invalidateQueries({
            queryKey: currentUserQueryOptions.queryKey,
          })
          const user = await loadCurrentUser()
          toast.success('Signed in successfully', {
            description: `${user.name} is now signed in.`,
          })
          return { type: 'authenticated', user }
        } catch (error) {
          // Login issued tokens, but staff bootstrap failed. Clear the half-session
          // so the login form can show a single recoverable error.
          tokenStore.clear('manual')
          queryClient.setQueryData(currentUserQueryOptions.queryKey, null)
          throw error
        }
      }

      return result
    },
    [currentUserQueryOptions.queryKey, loadCurrentUser, loginMutateAsync, queryClient, toast],
  )

  const verifyTwoFactor = useCallback(
    async (sessionToken: string, code: string): Promise<AuthUser> => {
      try {
        await verifyTwoFactorMutateAsync({ session_token: sessionToken, code })
        await queryClient.invalidateQueries({
          queryKey: currentUserQueryOptions.queryKey,
        })
        const user = await loadCurrentUser()
        toast.success('Signed in successfully', {
          description: `${user.name} is now signed in.`,
        })
        return user
      } catch (error) {
        if (tokenStore.getAccessToken()) {
          tokenStore.clear('manual')
          queryClient.setQueryData(currentUserQueryOptions.queryKey, null)
        }
        throw error
      }
    },
    [
      currentUserQueryOptions.queryKey,
      loadCurrentUser,
      queryClient,
      toast,
      verifyTwoFactorMutateAsync,
    ],
  )

  const signOut = useCallback(async (): Promise<void> => {
    try {
      await logoutMutateAsync()
    } finally {
      tokenStore.clear('logout')
      queryClient.clear()
      toast.success('Signed out', {
        description: 'You have been logged out of the workspace.',
      })
    }
  }, [logoutMutateAsync, queryClient, toast])

  const value = useMemo<AuthContextValue>(
    () => ({
      user: currentUserQuery.data ?? null,
      isAuthenticated: Boolean(currentUserQuery.data),
      isLoading: currentUserQuery.isPending && !currentUserQuery.data,
      accessIssue: isAuthAccessError(currentUserQuery.error) ? currentUserQuery.error.issue : null,
      login,
      verifyTwoFactor,
      signOut,
    }),
    [
      currentUserQuery.data,
      currentUserQuery.error,
      currentUserQuery.isPending,
      login,
      signOut,
      verifyTwoFactor,
    ],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
