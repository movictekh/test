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

export const authHandlers = [
  http.post(endpoint('/auth/login'), async ({ request }) => {
    await delay(250)
    const body = (await request.json()) as { email?: string; password?: string }

    if (!body.email || !body.password) {
      return HttpResponse.json({ detail: 'Email and password are required.' }, { status: 401 })
    }

    const profile =
      body.email === mockAuthUsers.client.user.email ? 'client' : 'service-administrator'
    activeProfile = profile

    return HttpResponse.json({
      success: true,
      access_token: `mock-access-${profile}`,
      refresh_token: `mock-refresh-${profile}`,
      user_id: mockAuthUsers[profile].user.id,
      detail: 'Login successful',
    })
  }),

  http.post(endpoint('/auth/refresh'), async ({ request }) => {
    const body = (await request.json()) as { refresh_token?: string }
    const profile = body.refresh_token?.includes('client') ? 'client' : 'service-administrator'
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
    if (!isAuthorized(request) || activeProfile !== 'service-administrator') {
      return HttpResponse.json({ detail: 'Role was not found.' }, { status: 404 })
    }

    return HttpResponse.json(mockAuthUsers['service-administrator'].role)
  }),

  http.get(endpoint('/clients/clients/profile'), ({ request }) => {
    if (!isAuthorized(request) || activeProfile !== 'client') {
      return HttpResponse.json({ detail: 'Client profile was not found.' }, { status: 404 })
    }

    return HttpResponse.json({ id: mockAuthUsers.client.user.id })
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
