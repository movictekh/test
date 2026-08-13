import { AUTH_ENDPOINTS } from '@/shared/auth/auth-endpoints'
import { tokenStore } from '@/shared/auth/token-store'
import { env } from '@/shared/config/env'

import { ApiError } from './api-error'

type RequestBody = BodyInit | object | null

interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  body?: RequestBody
  skipAuth?: boolean
  skipRefresh?: boolean
}

interface ApiErrorPayload {
  detail?: string
  message?: string
  code?: string
  errors?: unknown
}

interface RefreshTokenResponse {
  access_token: string
}

let refreshPromise: Promise<string | null> | null = null

function buildUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${env.apiBaseUrl}${normalizedPath}`
}

function isNativeBody(body: RequestBody): body is BodyInit {
  return (
    typeof body === 'string' ||
    body instanceof Blob ||
    body instanceof FormData ||
    body instanceof URLSearchParams ||
    body instanceof ArrayBuffer ||
    ArrayBuffer.isView(body)
  )
}

async function parseResponse(response: Response): Promise<unknown> {
  if (response.status === 204) return undefined

  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) return response.json()

  return response.text()
}

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise

  refreshPromise = (async () => {
    const refreshToken = tokenStore.getRefreshToken()
    if (!refreshToken) return null

    try {
      const response = await fetch(buildUrl(AUTH_ENDPOINTS.refresh), {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })

      if (!response.ok) {
        tokenStore.clear('expired')
        return null
      }

      const payload = (await response.json()) as RefreshTokenResponse
      tokenStore.updateAccessToken(payload.access_token)
      return payload.access_token
    } catch {
      tokenStore.clear('expired')
      return null
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}

async function executeRequest(
  path: string,
  options: ApiRequestOptions,
  accessToken?: string,
): Promise<Response> {
  const { body, skipAuth: _skipAuth, skipRefresh: _skipRefresh, ...requestOptions } = options
  void _skipAuth
  void _skipRefresh
  const headers = new Headers(requestOptions.headers)
  let requestBody: BodyInit | null | undefined

  if (body !== undefined) {
    if (isNativeBody(body)) requestBody = body
    else if (body === null) requestBody = null
    else {
      headers.set('Content-Type', 'application/json')
      requestBody = JSON.stringify(body)
    }
  }

  headers.set('Accept', 'application/json')

  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }

  const requestInit: RequestInit = {
    ...requestOptions,
    headers,
  }

  if (requestBody !== undefined) requestInit.body = requestBody

  return fetch(buildUrl(path), requestInit)
}

async function request<TResponse>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<TResponse> {
  let accessToken = options.skipAuth ? null : tokenStore.getAccessToken()

  if (!options.skipAuth && !options.skipRefresh && !accessToken && tokenStore.hasRefreshToken()) {
    accessToken = await refreshAccessToken()
  }

  let response: Response

  try {
    response = await executeRequest(path, options, accessToken ?? undefined)
  } catch (error) {
    throw new ApiError('The server could not be reached.', {
      status: 0,
      code: 'NETWORK_ERROR',
      cause: error,
    })
  }

  if (response.status === 401 && !options.skipAuth && !options.skipRefresh) {
    const refreshedAccessToken = await refreshAccessToken()

    if (refreshedAccessToken) {
      response = await executeRequest(path, { ...options, skipRefresh: true }, refreshedAccessToken)
    }
  }

  const payload = await parseResponse(response)

  if (!response.ok) {
    const errorPayload =
      typeof payload === 'object' && payload !== null ? (payload as ApiErrorPayload) : undefined

    if (response.status === 401 && !options.skipAuth) tokenStore.clear('expired')

    throw new ApiError(
      errorPayload?.detail ?? errorPayload?.message ?? 'The request could not be completed.',
      {
        status: response.status,
        ...(errorPayload?.code !== undefined ? { code: errorPayload.code } : {}),
        details: errorPayload?.errors ?? payload,
      },
    )
  }

  return payload as TResponse
}

function createBodyRequest<TResponse>(
  method: 'POST' | 'PUT' | 'PATCH',
  path: string,
  body: RequestBody | undefined,
  options: Omit<ApiRequestOptions, 'method' | 'body'> | undefined,
): Promise<TResponse> {
  return request<TResponse>(path, {
    ...options,
    method,
    ...(body !== undefined ? { body } : {}),
  })
}

export const apiClient = {
  get: <TResponse>(path: string, options?: Omit<ApiRequestOptions, 'method' | 'body'>) =>
    request<TResponse>(path, { ...options, method: 'GET' }),

  post: <TResponse>(
    path: string,
    body?: RequestBody,
    options?: Omit<ApiRequestOptions, 'method' | 'body'>,
  ) => createBodyRequest<TResponse>('POST', path, body, options),

  put: <TResponse>(
    path: string,
    body?: RequestBody,
    options?: Omit<ApiRequestOptions, 'method' | 'body'>,
  ) => createBodyRequest<TResponse>('PUT', path, body, options),

  patch: <TResponse>(
    path: string,
    body?: RequestBody,
    options?: Omit<ApiRequestOptions, 'method' | 'body'>,
  ) => createBodyRequest<TResponse>('PATCH', path, body, options),

  delete: <TResponse>(path: string, options?: Omit<ApiRequestOptions, 'method' | 'body'>) =>
    request<TResponse>(path, { ...options, method: 'DELETE' }),
}
