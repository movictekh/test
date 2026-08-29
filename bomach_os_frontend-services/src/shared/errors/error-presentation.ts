import { ApiError } from '@/shared/api/api-error'

export type ErrorPresentationContext =
  | 'default'
  | 'login'
  | 'two-factor'
  | 'form-submit'
  | 'page-load'
  | 'section-load'
  | 'background-action'
  | 'destructive-action'

export type ErrorPlacement = 'field' | 'form' | 'toast' | 'section' | 'page' | 'redirect'

export interface UserFacingError {
  title: string
  message: string
  placement: ErrorPlacement
  retryable: boolean
  fieldErrors?: Record<string, string>
}

interface ApiValidationDetails {
  [field: string]: unknown
}

const credentialMessages = [
  'invalid credentials',
  'invalid email or password',
  'incorrect email or password',
  'unable to log in with provided credentials',
  'no active account found',
  'user not found',
  'account not found',
  'wrong password',
]

const inactiveAccountMessages = ['inactive', 'disabled', 'suspended', 'blocked', 'deactivated']

function normalise(value: string): string {
  return value.trim().toLowerCase()
}

function containsAny(message: string, candidates: readonly string[]): boolean {
  const normalized = normalise(message)
  return candidates.some((candidate) => normalized.includes(candidate))
}

function firstString(value: unknown): string | undefined {
  if (typeof value === 'string' && value.trim()) return value.trim()

  if (Array.isArray(value)) {
    for (const item of value) {
      const result = firstString(item)
      if (result) return result
    }
  }

  return undefined
}

function extractFieldErrors(details: unknown): Record<string, string> | undefined {
  if (!details || typeof details !== 'object' || Array.isArray(details)) return undefined

  const entries = Object.entries(details as ApiValidationDetails)
    .map(([field, value]) => [field, firstString(value)] as const)
    .filter((entry): entry is readonly [string, string] => Boolean(entry[1]))

  return entries.length > 0 ? Object.fromEntries(entries) : undefined
}

function defaultNetworkError(): UserFacingError {
  return {
    title: 'Connection problem',
    message: 'We could not reach the server. Check your connection and try again.',
    placement: 'toast',
    retryable: true,
  }
}

function loginError(error: ApiError): UserFacingError {
  const message = error.message || ''

  if (error.status === 0 || error.code === 'NETWORK_ERROR') {
    return {
      ...defaultNetworkError(),
      placement: 'form',
    }
  }

  if (error.status === 429) {
    return {
      title: 'Too many login attempts',
      message: 'Please wait a moment before trying again.',
      placement: 'form',
      retryable: true,
    }
  }

  if (error.status === 401 || containsAny(message, credentialMessages)) {
    return {
      title: 'Sign-in unsuccessful',
      message: 'The email address or password is incorrect. Check both and try again.',
      placement: 'form',
      retryable: true,
    }
  }

  if (error.status === 403 && containsAny(message, inactiveAccountMessages)) {
    return {
      title: 'Account unavailable',
      message: 'This account is not currently active. Contact an administrator for assistance.',
      placement: 'form',
      retryable: false,
    }
  }

  if (error.status === 403) {
    return {
      title: 'Sign-in not permitted',
      message: 'This account cannot access the Service Operations workspace.',
      placement: 'form',
      retryable: false,
    }
  }

  if (error.status >= 500) {
    return {
      title: 'Sign-in service unavailable',
      message: 'The sign-in service is temporarily unavailable. Please try again shortly.',
      placement: 'form',
      retryable: true,
    }
  }

  return {
    title: 'Sign-in unsuccessful',
    message: 'We could not sign you in. Review your details and try again.',
    placement: 'form',
    retryable: true,
  }
}

function twoFactorError(error: ApiError): UserFacingError {
  if (error.status === 0 || error.code === 'NETWORK_ERROR') {
    return {
      ...defaultNetworkError(),
      placement: 'form',
    }
  }

  if ([400, 401].includes(error.status)) {
    return {
      title: 'Code not accepted',
      message: 'The verification code is incorrect or has expired. Enter a new code and try again.',
      placement: 'form',
      retryable: true,
    }
  }

  if (error.status === 429) {
    return {
      title: 'Too many attempts',
      message: 'Please wait before requesting or entering another verification code.',
      placement: 'form',
      retryable: true,
    }
  }

  return {
    title: 'Verification unsuccessful',
    message: 'We could not verify the code. Please try again.',
    placement: 'form',
    retryable: true,
  }
}

function validationError(error: ApiError): UserFacingError {
  const fieldErrors = extractFieldErrors(error.details)

  return {
    title: 'Check the highlighted information',
    message: fieldErrors
      ? 'Some information needs your attention before this can be submitted.'
      : 'Review the form and correct the information that could not be accepted.',
    placement: 'form',
    retryable: true,
    ...(fieldErrors ? { fieldErrors } : {}),
  }
}

export function presentError(
  error: unknown,
  context: ErrorPresentationContext = 'default',
): UserFacingError {
  if (!(error instanceof ApiError)) {
    return {
      title: 'Something went wrong',
      message: 'An unexpected error occurred. Please try again.',
      placement:
        context === 'page-load' ? 'page' : context === 'section-load' ? 'section' : 'toast',
      retryable: true,
    }
  }

  if (context === 'login') return loginError(error)
  if (context === 'two-factor') return twoFactorError(error)

  if (error.status === 0 || error.code === 'NETWORK_ERROR') {
    const networkError = defaultNetworkError()

    if (context === 'page-load') return { ...networkError, placement: 'page' }
    if (context === 'section-load') return { ...networkError, placement: 'section' }
    if (context === 'form-submit') return { ...networkError, placement: 'form' }

    return networkError
  }

  if (error.status === 400 || error.status === 422) {
    return validationError(error)
  }

  if (error.status === 401) {
    return {
      title: 'Session expired',
      message: 'Sign in again to continue.',
      placement: 'redirect',
      retryable: false,
    }
  }

  if (error.status === 403) {
    return {
      title: 'Permission required',
      message: 'You do not have permission to complete this action.',
      placement:
        context === 'page-load' ? 'page' : context === 'section-load' ? 'section' : 'toast',
      retryable: false,
    }
  }

  if (error.status === 404) {
    return {
      title: 'Record not found',
      message: 'This record may have been removed or you may no longer have access to it.',
      placement: context === 'page-load' ? 'page' : 'toast',
      retryable: false,
    }
  }

  if (error.status === 409) {
    return {
      title: 'The record has changed',
      message: 'Refresh the latest information before trying this action again.',
      placement: context === 'form-submit' ? 'form' : 'toast',
      retryable: true,
    }
  }

  if (error.status === 429) {
    return {
      title: 'Too many requests',
      message: 'Please wait a moment before trying again.',
      placement: context === 'form-submit' ? 'form' : 'toast',
      retryable: true,
    }
  }

  if (error.status >= 500) {
    return {
      title: 'Service temporarily unavailable',
      message: 'The server could not complete this request. Please try again shortly.',
      placement:
        context === 'page-load'
          ? 'page'
          : context === 'section-load'
            ? 'section'
            : context === 'form-submit'
              ? 'form'
              : 'toast',
      retryable: true,
    }
  }

  return {
    title: 'Action unsuccessful',
    message: 'The action could not be completed. Please try again.',
    placement: context === 'form-submit' ? 'form' : 'toast',
    retryable: true,
  }
}

export function getUserFacingErrorMessage(
  error: unknown,
  context: ErrorPresentationContext = 'default',
): string {
  return presentError(error, context).message
}
