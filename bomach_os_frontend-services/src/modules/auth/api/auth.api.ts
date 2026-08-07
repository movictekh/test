import { ApiError } from '@/shared/api/api-error'
import { apiClient } from '@/shared/api/api-client'
import { AUTH_ENDPOINTS } from '@/shared/auth/auth-endpoints'
import { tokenStore } from '@/shared/auth/token-store'

import { AuthAccessError } from '../errors/auth-access-error'
import { mapAuthenticatedUser } from '../mappers/auth.mapper'
import type {
  AuthorityLimitsResponseDto,
  ForgotPasswordRequestDto,
  LoginRequestDto,
  LoginResponseDto,
  LogoutResponseDto,
  PermissionsMapResponseDto,
  ResetPasswordRequestDto,
  SuccessDetailResponseDto,
  RoleResponseDto,
  TwoFactorRequiredResponseDto,
  TwoFactorStatusResponseDto,
  TwoFactorToggleRequestDto,
  TwoFactorToggleResponseDto,
  TwoFactorVerifyRequestDto,
  TwoFactorVerifyResponseDto,
  UserResponseDto,
  VerifyTokenResponseDto,
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
  try {
    const role = await apiClient.get<RoleResponseDto>(AUTH_ENDPOINTS.employeeRole(user.id))
    return mapAuthenticatedUser(user, role)
  } catch (error) {
    if (error instanceof ApiError && error.status === 403) {
      if (error.message === 'Employee profile not found.') {
        throw new AuthAccessError('employee-profile-missing', error.message)
      }

      if (
        error.message === 'No role assigned.' ||
        error.message === 'No role assigned to this employee.'
      ) {
        throw new AuthAccessError('role-missing', error.message)
      }

      throw new AuthAccessError('role-access-denied', error.message)
    }

    throw error
  }
}

async function login(credentials: LoginCredentials): Promise<LoginResult> {
  const payload: LoginRequestDto = {
    email: credentials.email,
    password: credentials.password,
  }

  const response = await apiClient.post<LoginResponseDto | TwoFactorRequiredResponseDto>(
    AUTH_ENDPOINTS.login,
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
  const response = await apiClient.post<TwoFactorVerifyResponseDto>(
    AUTH_ENDPOINTS.verifyTwoFactor,
    payload,
    {
      skipAuth: true,
      skipRefresh: true,
    },
  )

  persistLoginTokens(response)
}

async function currentUser(): Promise<AuthenticatedUser | null> {
  if (!tokenStore.getAccessToken() && !tokenStore.hasRefreshToken()) return null

  try {
    const user = await apiClient.get<UserResponseDto>(AUTH_ENDPOINTS.me)
    return await loadStaffUser(user)
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null
    throw error
  }
}

async function logout(): Promise<void> {
  try {
    await apiClient.post<LogoutResponseDto>(AUTH_ENDPOINTS.logout)
  } finally {
    tokenStore.clear('logout')
  }
}

async function getTwoFactorStatus(): Promise<TwoFactorStatusResponseDto> {
  return apiClient.get<TwoFactorStatusResponseDto>(AUTH_ENDPOINTS.twoFactorStatus)
}

async function enableTwoFactor(
  payload: TwoFactorToggleRequestDto,
): Promise<TwoFactorToggleResponseDto> {
  return apiClient.post<TwoFactorToggleResponseDto>(AUTH_ENDPOINTS.enableTwoFactor, payload)
}

async function disableTwoFactor(
  payload: TwoFactorToggleRequestDto,
): Promise<TwoFactorToggleResponseDto> {
  return apiClient.post<TwoFactorToggleResponseDto>(AUTH_ENDPOINTS.disableTwoFactor, payload)
}

async function forgotPassword(
  payload: ForgotPasswordRequestDto,
): Promise<SuccessDetailResponseDto> {
  return apiClient.post<SuccessDetailResponseDto>(AUTH_ENDPOINTS.forgotPassword, payload, {
    skipAuth: true,
    skipRefresh: true,
  })
}

async function resetPassword(payload: ResetPasswordRequestDto): Promise<SuccessDetailResponseDto> {
  return apiClient.post<SuccessDetailResponseDto>(AUTH_ENDPOINTS.resetPassword, payload, {
    skipAuth: true,
    skipRefresh: true,
  })
}

async function verifyToken(): Promise<VerifyTokenResponseDto> {
  return apiClient.get<VerifyTokenResponseDto>(AUTH_ENDPOINTS.verifyToken)
}

async function getPermissionsMap(): Promise<PermissionsMapResponseDto> {
  return apiClient.get<PermissionsMapResponseDto>(AUTH_ENDPOINTS.permissionsMap)
}

async function getAuthorityLimits(): Promise<AuthorityLimitsResponseDto> {
  return apiClient.get<AuthorityLimitsResponseDto>(AUTH_ENDPOINTS.authorityLimits)
}

export const authApi = {
  login,
  verifyTwoFactor,
  getTwoFactorStatus,
  enableTwoFactor,
  disableTwoFactor,
  currentUser,
  verifyToken,
  forgotPassword,
  resetPassword,
  getPermissionsMap,
  getAuthorityLimits,
  logout,
}
