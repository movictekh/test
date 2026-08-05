import { ApiError } from '@/shared/api/api-error'
import { apiClient } from '@/shared/api/api-client'
import { tokenStore } from '@/shared/auth/token-store'

import { mapAuthenticatedUser } from '../mappers/auth.mapper'
import type {
  LoginRequestDto,
  LoginResponseDto,
  LogoutResponseDto,
  RoleResponseDto,
  TwoFactorRequiredResponseDto,
  TwoFactorVerifyRequestDto,
  TwoFactorVerifyResponseDto,
  UserResponseDto,
} from '../types/auth.contracts'
import type { AuthenticatedUser, LoginCredentials, LoginResult } from '../types/auth.types'

function isTwoFactorRequired(
  response: LoginResponseDto | TwoFactorRequiredResponseDto,
): response is TwoFactorRequiredResponseDto {
  return 'requires_2fa' in response && response.requires_2fa === true
}

function persistLoginTokens(response: LoginResponseDto): void {
  tokenStore.set({
    accessToken: response.access_token,
    refreshToken: response.refresh_token,
  })
}

async function detectUserContext(user: UserResponseDto): Promise<AuthenticatedUser> {
  try {
    const role = await apiClient.get<RoleResponseDto>(`/roles/employees/${user.id}`)
    return mapAuthenticatedUser(user, role, 'staff')
  } catch (error) {
    if (!(error instanceof ApiError) || ![403, 404].includes(error.status)) throw error

    await apiClient.get<unknown>('/clients/clients/profile')
    return mapAuthenticatedUser(user, null, 'client')
  }
}

async function login(credentials: LoginCredentials): Promise<LoginResult> {
  const payload: LoginRequestDto = {
    email: credentials.email,
    password: credentials.password,
  }

  const response = await apiClient.post<LoginResponseDto | TwoFactorRequiredResponseDto>(
    '/auth/login',
    payload,
    { skipAuth: true, skipRefresh: true },
  )

  if (isTwoFactorRequired(response)) {
    return {
      type: 'two-factor-required',
      sessionToken: response.session_token,
      detail: response.detail,
    }
  }

  persistLoginTokens(response)
  return { type: 'authenticated' }
}

async function verifyTwoFactor(payload: TwoFactorVerifyRequestDto): Promise<void> {
  const response = await apiClient.post<TwoFactorVerifyResponseDto>('/auth/verify-2fa', payload, {
    skipAuth: true,
    skipRefresh: true,
  })

  persistLoginTokens(response)
}

async function currentUser(): Promise<AuthenticatedUser | null> {
  if (!tokenStore.get()) return null

  try {
    const user = await apiClient.get<UserResponseDto>('/auth/me')
    return await detectUserContext(user)
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null
    throw error
  }
}

async function logout(): Promise<void> {
  try {
    await apiClient.post<LogoutResponseDto>('/auth/logout')
  } finally {
    tokenStore.clear()
  }
}

export const authApi = {
  login,
  verifyTwoFactor,
  currentUser,
  logout,
}
