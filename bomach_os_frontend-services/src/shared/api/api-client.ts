import { env } from '@/shared/config/env'

import { ApiError } from './api-error'

type RequestBody = BodyInit | Record<string, unknown> | unknown[] | null

interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  body?: RequestBody
}

interface ApiErrorPayload {
  message?: string
  code?: string
  errors?: unknown
}

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
  if (response.status === 204) {
    return undefined
  }

  const contentType = response.headers.get('content-type') ?? ''

  if (contentType.includes('application/json')) {
    return response.json()
  }

  return response.text()
}

async function request<TResponse>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<TResponse> {
  const { body, ...requestOptions } = options
  const headers = new Headers(requestOptions.headers)
  let requestBody: BodyInit | null | undefined

  if (body !== undefined) {
    if (isNativeBody(body)) {
      requestBody = body
    } else if (body === null) {
      requestBody = null
    } else {
      headers.set('Content-Type', 'application/json')
      requestBody = JSON.stringify(body)
    }
  }

  headers.set('Accept', 'application/json')

  let response: Response

  const requestInit: RequestInit = {
    ...requestOptions,
    headers,
    credentials: 'include',
  }

  if (requestBody !== undefined) {
    requestInit.body = requestBody
  }

  try {
    response = await fetch(buildUrl(path), requestInit)
  } catch (error) {
    throw new ApiError('The server could not be reached.', {
      status: 0,
      code: 'NETWORK_ERROR',
      cause: error,
    })
  }

  const payload = await parseResponse(response)

  if (!response.ok) {
    const errorPayload =
      typeof payload === 'object' && payload !== null ? (payload as ApiErrorPayload) : undefined

    throw new ApiError(errorPayload?.message ?? 'The request could not be completed.', {
      status: response.status,
      ...(errorPayload?.code !== undefined ? { code: errorPayload.code } : {}),
      details: errorPayload?.errors ?? payload,
    })
  }

  return payload as TResponse
}

function createBodyRequest<TResponse>(
  method: 'POST' | 'PUT' | 'PATCH',
  path: string,
  body: RequestBody | undefined,
  options: Omit<ApiRequestOptions, 'method' | 'body'> | undefined,
): Promise<TResponse> {
  if (body === undefined) {
    return request<TResponse>(path, {
      ...options,
      method,
    })
  }

  return request<TResponse>(path, {
    ...options,
    method,
    body,
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
