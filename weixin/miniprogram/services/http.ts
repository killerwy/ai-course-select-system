import { DEVELOPMENT_ENV, normalizeBaseUrl } from '../config/env'
import {
  errorMessage,
  isErrorEnvelope,
  isSuccessEnvelope,
} from '../domain/guards'
import type {
  ApiErrorDetail,
  ErrorEnvelope,
  ResponseMeta,
} from '../domain/types'

export type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'

export interface TransportRequest {
  url: string
  method: HttpMethod
  headers: Record<string, string>
  data?: unknown
  timeoutMs: number
}

export interface TransportResponse {
  statusCode: number
  data: unknown
  headers?: Record<string, string>
}

export interface RequestTransport {
  request(options: TransportRequest): Promise<TransportResponse>
}

export interface RequestOptions {
  method?: HttpMethod
  data?: unknown
  headers?: Record<string, string>
  idempotencyKey?: string
  requestId?: string
  timeoutMs?: number
  requiresAuth?: boolean
}

export interface HttpResult<T> {
  data: T
  meta: ResponseMeta
  compat: 'envelope' | 'naked-array' | 'naked-object'
}

export interface ApiClientOptions {
  baseUrl?: string
  transport?: RequestTransport
  getAccessToken?: () => string | undefined
  onUnauthorized?: () => void
}

export class ApiError extends Error {
  readonly code: string
  readonly statusCode: number
  readonly details: ApiErrorDetail[]
  readonly requestId: string
  readonly retryable: boolean

  constructor(options: {
    code: string
    message: string
    statusCode?: number
    details?: ApiErrorDetail[]
    requestId?: string
    retryable?: boolean
  }) {
    super(options.message)
    this.name = 'ApiError'
    this.code = options.code
    this.statusCode = options.statusCode ?? 0
    this.details = options.details ?? []
    this.requestId = options.requestId ?? ''
    this.retryable = options.retryable ?? false
  }
}

function compactId(value: string): string {
  return value.replace(/[^a-zA-Z0-9:_-]/g, '-').slice(0, 64)
}

export function createRequestId(scope = 'wx'): string {
  return compactId(scope + ':' + Date.now().toString(36) + ':' + Math.random().toString(36).slice(2, 10))
}

export function createIdempotencyKey(scope: string, seed = createRequestId('idem')): string {
  const value = compactId(scope + ':' + seed)
  if (!value || value.length > 64) {
    throw new ApiError({
      code: 'INVALID_IDEMPOTENCY_KEY',
      message: '幂等键格式无效',
    })
  }
  return value
}

function compatMeta(requestId: string): ResponseMeta {
  return { request_id: requestId || createRequestId('compat') }
}

export function unwrapResponse<T>(payload: unknown, requestId = ''): HttpResult<T> {
  if (isErrorEnvelope(payload)) {
    throw apiErrorFromEnvelope(payload)
  }
  if (isSuccessEnvelope<T>(payload)) {
    return { data: payload.data, meta: payload.meta, compat: 'envelope' }
  }
  if (Array.isArray(payload)) {
    return { data: payload as T, meta: compatMeta(requestId), compat: 'naked-array' }
  }
  if (payload !== null && typeof payload === 'object') {
    return { data: payload as T, meta: compatMeta(requestId), compat: 'naked-object' }
  }
  throw new ApiError({
    code: 'INVALID_RESPONSE',
    message: '服务端响应格式无效',
    requestId,
  })
}

function apiErrorFromEnvelope(envelope: ErrorEnvelope, statusCode = 0): ApiError {
  const code = envelope.error.code
  return new ApiError({
    code,
    message: errorMessage(code, envelope.error.message),
    statusCode,
    details: envelope.error.details,
    requestId: envelope.meta.request_id,
    retryable: statusCode >= 500,
  })
}

function responseError(response: TransportResponse, requestId: string): ApiError {
  if (isErrorEnvelope(response.data)) {
    return apiErrorFromEnvelope(response.data, response.statusCode)
  }
  const code = response.statusCode === 401
    ? 'UNAUTHORIZED'
    : response.statusCode === 403
      ? 'FORBIDDEN'
      : response.statusCode >= 500
        ? 'INTERNAL_ERROR'
        : 'HTTP_' + response.statusCode
  return new ApiError({
    code,
    message: errorMessage(code, '请求失败（' + response.statusCode + '）'),
    statusCode: response.statusCode,
    requestId,
    retryable: response.statusCode >= 500,
  })
}

function networkError(reason: unknown): ApiError {
  const message = reason instanceof Error ? reason.message : String(reason)
  const timeout = /timeout/i.test(message)
  const code = timeout ? 'REQUEST_TIMEOUT' : 'NETWORK_ERROR'
  return new ApiError({
    code,
    message: errorMessage(code),
    retryable: true,
  })
}

export function createWxTransport(): RequestTransport {
  return {
    request(options: TransportRequest): Promise<TransportResponse> {
      return new Promise((resolve, reject) => {
        wx.request({
          url: options.url,
          method: options.method,
          header: options.headers,
          data: options.data,
          timeout: options.timeoutMs,
          success: response => resolve({
            statusCode: response.statusCode,
            data: response.data,
            headers: response.header as Record<string, string>,
          }),
          fail: error => reject(new Error(error.errMsg)),
        })
      })
    },
  }
}

export function createApiClient(options: ApiClientOptions = {}) {
  const baseUrl = normalizeBaseUrl(options.baseUrl ?? DEVELOPMENT_ENV.apiBaseUrl)
  const transport = options.transport ?? createWxTransport()

  async function request<T>(path: string, requestOptions: RequestOptions = {}): Promise<HttpResult<T>> {
    const method = requestOptions.method ?? 'GET'
    const requestId = requestOptions.requestId ?? createRequestId()
    const headers: Record<string, string> = {
      Accept: 'application/json',
      'X-Request-ID': requestId,
      ...requestOptions.headers,
    }
    const token = options.getAccessToken?.()
    if (requestOptions.requiresAuth !== false && token) {
      headers.Authorization = 'Bearer ' + token
    }
    if (method !== 'GET') {
      const idempotencyKey = requestOptions.idempotencyKey ?? createIdempotencyKey(path, requestId)
      if (idempotencyKey.length === 0 || idempotencyKey.length > 64) {
        throw new ApiError({ code: 'INVALID_IDEMPOTENCY_KEY', message: '幂等键格式无效' })
      }
      headers['Idempotency-Key'] = idempotencyKey
    }

    let response: TransportResponse
    try {
      response = await transport.request({
        url: baseUrl + (path.startsWith('/') ? path : '/' + path),
        method,
        headers,
        data: requestOptions.data,
        timeoutMs: requestOptions.timeoutMs ?? DEVELOPMENT_ENV.timeoutMs,
      })
    } catch (error) {
      throw error instanceof ApiError ? error : networkError(error)
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      const error = responseError(response, requestId)
      if (error.statusCode === 401 || error.code === 'UNAUTHORIZED' || error.code === 'INVALID_TOKEN') {
        options.onUnauthorized?.()
      }
      throw error
    }
    return unwrapResponse<T>(response.data, requestId)
  }

  return { request }
}
