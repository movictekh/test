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

async function loadStaffUser(user: UserResponseDto): Promise<AuthenticatedUser> {
  const role = await apiClient.get<RoleResponseDto>(`/roles/employees/${user.id}`)
  return mapAuthenticatedUser(user, role)
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
  if (!tokenStore.getAccessToken() && !tokenStore.hasRefreshToken()) return null

  try {
    const user = await apiClient.get<UserResponseDto>('/auth/me')
    return await loadStaffUser(user)
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null
    throw error
  }
}

async function logout(): Promise<void> {
  try {
    await apiClient.post<LogoutResponseDto>('/auth/logout')
  } finally {
    tokenStore.clear('logout')
  }
}

export const authApi = {
  login,
  verifyTwoFactor,
  currentUser,
  logout,
}
