export interface LoginRequestDto {
  email: string
  password: string
}

export interface LoginResponseDto {
  success: boolean
  access_token: string
  refresh_token: string
  user_id: number
  detail: string
}

export interface TwoFactorRequiredResponseDto {
  success: boolean
  requires_2fa: true
  session_token: string
  detail: string
}

export interface TwoFactorVerifyRequestDto {
  session_token: string
  code: string
}

export type TwoFactorVerifyResponseDto = LoginResponseDto

export interface LogoutResponseDto {
  success: boolean
  detail: string
}

export interface UserResponseDto {
  id: number
  email: string
  username: string
  first_name: string | null
  last_name: string | null
  phone_number: string | null
  is_verified: boolean
  created_at: string
}

export interface BranchMinimalDto {
  id: number
  branch_name: string
}

export interface RoleResponseDto {
  id: number
  name: string
  branches: BranchMinimalDto[]
  permissions: Record<string, string[]>
  created_at: string
  updated_at: string
}

export interface ErrorResponseDto {
  detail: string
}

export interface RefreshTokenRequestDto {
  refresh_token: string
}

export interface RefreshTokenResponseDto {
  success: boolean
  access_token: string
  detail: string
}

export interface TwoFactorStatusResponseDto {
  success: boolean
  two_factor_enabled: boolean
}

export interface TwoFactorToggleRequestDto {
  password: string
}

export type TwoFactorToggleResponseDto = TwoFactorStatusResponseDto

export interface ForgotPasswordRequestDto {
  email: string
}

export interface ResetPasswordRequestDto {
  email: string
  code: string
  new_password: string
}

export interface SuccessDetailResponseDto {
  success: boolean
  detail: string
}

export interface VerifyTokenResponseDto {
  success: boolean
  valid: boolean
  user_id: number | null
  detail: string
}

export interface PermissionsMapResponseDto {
  permissions_map: Record<string, string[]>
}

export interface AuthorityLimitItemDto {
  resource: string
  action: string
  label: string
  helper_text: string
}

export interface AuthorityLimitsResponseDto {
  items: AuthorityLimitItemDto[]
}
