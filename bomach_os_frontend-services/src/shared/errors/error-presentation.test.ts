import { describe, expect, it } from 'vitest'

import { ApiError } from '@/shared/api/api-error'

import { presentError } from './error-presentation'

describe('presentError', () => {
  it('does not reveal whether the email or password was wrong', () => {
    const result = presentError(
      new ApiError('No active account found with the given credentials', {
        status: 401,
      }),
      'login',
    )

    expect(result).toMatchObject({
      title: 'Sign-in unsuccessful',
      message: 'The email address or password is incorrect. Check both and try again.',
      placement: 'form',
    })
  })

  it('maps validation details to field errors', () => {
    const result = presentError(
      new ApiError('Validation failed', {
        status: 422,
        details: {
          email: ['Enter a valid email address.'],
          budget: ['Budget must be greater than zero.'],
        },
      }),
      'form-submit',
    )

    expect(result.fieldErrors).toEqual({
      email: 'Enter a valid email address.',
      budget: 'Budget must be greater than zero.',
    })
  })

  it('places page loading failures at page level', () => {
    const result = presentError(
      new ApiError('Server error', {
        status: 500,
      }),
      'page-load',
    )

    expect(result.placement).toBe('page')
  })

  it('places background action failures in a toast', () => {
    const result = presentError(
      new ApiError('Conflict', {
        status: 409,
      }),
      'background-action',
    )

    expect(result.placement).toBe('toast')
  })
})
