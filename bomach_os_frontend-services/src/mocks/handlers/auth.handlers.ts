import { delay, http, HttpResponse } from 'msw'

import { env } from '@/shared/config/env'

import { mockAuthUsers } from '../data/auth.mock'

let activeProfile: keyof typeof mockAuthUsers | null = null

function endpoint(path: string): string {
  return `${env.apiBaseUrl}${path}`
}

function isAuthorized(request: Request): boolean {
  return request.headers.get('authorization')?.startsWith('Bearer mock-access-') ?? false
}

function authenticate(email: string, password: string): keyof typeof mockAuthUsers | null {
  for (const [profile, account] of Object.entries(mockAuthUsers)) {
    if (account.user.email === email && account.password === password) {
      return profile as keyof typeof mockAuthUsers
    }
  }

  return null
}

export const authHandlers = [
  http.post(endpoint('/auth/login'), async ({ request }) => {
    await delay(250)
    const body = (await request.json()) as { email?: string; password?: string }

    if (!body.email || !body.password) {
      return HttpResponse.json({ detail: 'Email and password are required.' }, { status: 401 })
    }

    const profile = authenticate(body.email, body.password)

    if (!profile) {
      return HttpResponse.json(
        { detail: 'No active account found with the given credentials.' },
        { status: 401 },
      )
    }

    activeProfile = profile

    return HttpResponse.json({
      success: true,
      access_token: `mock-access-${profile}`,
      refresh_token: `mock-refresh-${profile}`,
      user_id: mockAuthUsers[profile].user.id,
      detail: 'Login successful',
    })
  }),

  http.post(endpoint('/auth/refresh'), () => {
    const profile = activeProfile ?? 'service-administrator'
    activeProfile = profile

    return HttpResponse.json({
      success: true,
      access_token: `mock-access-${profile}-refreshed`,
      detail: 'Token refreshed successfully',
    })
  }),

  http.get(endpoint('/auth/me'), ({ request }) => {
    if (!isAuthorized(request) || !activeProfile) {
      return HttpResponse.json(
        { detail: 'Authentication credentials were not provided.' },
        { status: 401 },
      )
    }

    return HttpResponse.json(mockAuthUsers[activeProfile].user)
  }),

  http.get(endpoint('/roles/employees/:userId'), ({ request }) => {
    if (!isAuthorized(request) || !activeProfile) {
      return HttpResponse.json({ detail: 'Role was not found.' }, { status: 404 })
    }

    return HttpResponse.json(mockAuthUsers[activeProfile].role)
  }),

  http.post(endpoint('/auth/logout'), () => {
    activeProfile = null
    return HttpResponse.json({ success: true, detail: 'Logged out successfully' })
  }),

  http.post(endpoint('/auth/verify-2fa'), () =>
    HttpResponse.json(
      { detail: 'Two-factor authentication is not enabled for the default mock profiles.' },
      { status: 400 },
    ),
  ),
]
