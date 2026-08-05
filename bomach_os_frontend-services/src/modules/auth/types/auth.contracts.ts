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
  name: string
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
