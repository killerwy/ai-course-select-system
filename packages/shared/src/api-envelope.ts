export interface ResponseMeta {
  request_id: string
}

export interface SuccessEnvelope<T> {
  data: T
  meta: ResponseMeta
}

export interface ErrorDetail {
  code: string
  message: string
  details?: unknown[]
}

export interface ErrorEnvelope {
  error: ErrorDetail
  meta: ResponseMeta
}

export interface HttpResult<T> {
  data: T
  meta: ResponseMeta
  compat: 'envelope' | 'naked-array' | 'naked-object'
}

export class ApiError extends Error {
  readonly code: string
  readonly statusCode: number
  readonly details: unknown[]
  readonly requestId: string
  readonly retryable: boolean

  constructor(options: {
    code: string
    message: string
    statusCode?: number
    details?: unknown[]
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

export function isSuccessEnvelope<T>(payload: unknown): payload is SuccessEnvelope<T> {
  return (
    payload !== null &&
    typeof payload === 'object' &&
    'data' in payload &&
    'meta' in payload &&
    typeof (payload as SuccessEnvelope<T>).meta === 'object' &&
    (payload as SuccessEnvelope<T>).meta !== null &&
    'request_id' in (payload as SuccessEnvelope<T>).meta
  )
}

export function isErrorEnvelope(payload: unknown): payload is ErrorEnvelope {
  return (
    payload !== null &&
    typeof payload === 'object' &&
    'error' in payload &&
    'meta' in payload &&
    typeof (payload as ErrorEnvelope).error === 'object' &&
    (payload as ErrorEnvelope).error !== null &&
    'code' in (payload as ErrorEnvelope).error
  )
}

const ERROR_MESSAGES: Record<string, string> = {
  UNAUTHORIZED: '请先登录',
  FORBIDDEN: '权限不足',
  NOT_FOUND: '资源不存在',
  VALIDATION_ERROR: '输入验证失败',
  INTERNAL_ERROR: '服务器内部错误',
  NETWORK_ERROR: '网络请求失败',
  REQUEST_TIMEOUT: '请求超时',
  DUPLICATE: '已选过该课程，不能重复选课。',
  CONFLICT: '时间冲突：该课程与已选课程的上课时间重叠，不能选课。',
  TIME_CONFLICT: '时间冲突：该课程与已选课程的上课时间重叠，不能选课。',
  PREREQUISITE_MISSING: '缺少前置课程：请先完成要求的前置课程后再选课。',
  CAPACITY_FULL: '课程已满，当前不能直接选课，可以加入候补。',
  WAITLIST_ALLOWED: '课程已满，可以加入候补。',
  COURSE_CLOSED: '课程已关闭，暂时不能选课。',
  COURSE_CANCELLED: '课程已取消，不能选课。',
  EXCEPTION_REQUIRED: '当前选课需要审批，请先提交审批申请。',
  INVALID_SCHEDULE: '课程时间安排无效',
  INVALID_CAPACITY_DELTA: '容量变更无效',
  INVALID_COURSE_OPERATION: '无效的课程操作',
  COURSE_NOT_FOUND: '课程不存在',
  ENROLLMENT_NOT_FOUND: '选课记录不存在',
  APPROVAL_NOT_PENDING: '审批不在待处理状态',
  APPROVAL_RECHECK_FAILED: '审批复核失败',
  EMPTY_COMMENT: '审批意见不能为空',
  APPROVAL_RULE_NOT_ALLOWED: '不允许豁免此规则',
  COURSE_ALREADY_EXISTS: '课程已存在',
  COURSE_OPERATION_NOT_PENDING: '课程操作不在待处理状态',
}

export function errorMessage(code: string, fallback?: string): string {
  return ERROR_MESSAGES[code] ?? fallback ?? '请求失败'
}

function compatMeta(requestId: string): ResponseMeta {
  return { request_id: requestId || `compat:${Date.now()}` }
}

export function unwrapResponse<T>(payload: unknown, requestId = ''): HttpResult<T> {
  if (isErrorEnvelope(payload)) {
    throw new ApiError({
      code: payload.error.code,
      message: errorMessage(payload.error.code, payload.error.message),
      statusCode: 0,
      details: payload.error.details ?? [],
      requestId: payload.meta.request_id,
      retryable: false,
    })
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
