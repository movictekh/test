import { mutationOptions } from '@tanstack/react-query'

import { authApi } from './auth.api'
import type { LoginCredentials } from '../types/auth.types'
import type { TwoFactorVerifyRequestDto } from '../types/auth.contracts'

export const authMutations = {
  login: () =>
    mutationOptions({
      mutationFn: (credentials: LoginCredentials) => authApi.login(credentials),
    }),
  verifyTwoFactor: () =>
    mutationOptions({
      mutationFn: (payload: TwoFactorVerifyRequestDto) => authApi.verifyTwoFactor(payload),
    }),
  logout: () => mutationOptions({ mutationFn: () => authApi.logout() }),
}
