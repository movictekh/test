export type AuthAccessIssue = 'employee-profile-missing' | 'role-missing' | 'role-access-denied'

export class AuthAccessError extends Error {
  constructor(
    public readonly issue: AuthAccessIssue,
    message: string,
  ) {
    super(message)
    this.name = 'AuthAccessError'
  }
}

export function isAuthAccessError(error: unknown): error is AuthAccessError {
  return error instanceof AuthAccessError
}
