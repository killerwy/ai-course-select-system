import {
  APPROVAL_STATUSES,
  COURSE_STATUSES,
  ENROLLMENT_STATUSES,
  ERROR_MESSAGES,
  RECOMMENDATION_STATUSES,
  ROLES,
  RUN_STATUSES,
  STATUS_LABELS,
  WAITLIST_STATUSES,
  type CourseSchedule,
  type CourseSummary,
  type ErrorEnvelope,
  type ResponseMeta,
  type Role,
  type RunStatus,
  type SuccessEnvelope,
} from './types'

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function hasString(value: Record<string, unknown>, key: string): boolean {
  return typeof value[key] === 'string' && value[key] !== ''
}

function hasNumber(value: Record<string, unknown>, key: string): boolean {
  return typeof value[key] === 'number' && Number.isFinite(value[key])
}

export function isOneOf<T extends readonly string[]>(value: unknown, values: T): value is T[number] {
  return typeof value === 'string' && values.includes(value)
}

export const isRole = (value: unknown): value is Role => isOneOf(value, ROLES)
export const isCourseStatus = (value: unknown): boolean => isOneOf(value, COURSE_STATUSES)
export const isEnrollmentStatus = (value: unknown): boolean => isOneOf(value, ENROLLMENT_STATUSES)
export const isWaitlistStatus = (value: unknown): boolean => isOneOf(value, WAITLIST_STATUSES)
export const isRecommendationStatus = (value: unknown): boolean => isOneOf(value, RECOMMENDATION_STATUSES)
export const isApprovalStatus = (value: unknown): boolean => isOneOf(value, APPROVAL_STATUSES)
export const isRunStatus = (value: unknown): value is RunStatus => isOneOf(value, RUN_STATUSES)

export function statusLabel(status: unknown): string {
  return typeof status === 'string' && STATUS_LABELS[status] ? STATUS_LABELS[status] : '未知'
}

export function errorMessage(code: unknown, fallback = '请求失败，请稍后重试'): string {
  return typeof code === 'string' && ERROR_MESSAGES[code] ? ERROR_MESSAGES[code] : fallback
}

export function isTerminalRunStatus(status: unknown): status is 'SUCCEEDED' | 'FAILED' {
  return status === 'SUCCEEDED' || status === 'FAILED'
}

export function isResponseMeta(value: unknown): value is ResponseMeta {
  return isRecord(value) && hasString(value, 'request_id')
}

export function isSuccessEnvelope<T = unknown>(value: unknown): value is SuccessEnvelope<T> {
  return isRecord(value) && 'data' in value && isResponseMeta(value.meta)
}

export function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (!isRecord(value) || !isRecord(value.error) || !isResponseMeta(value.meta)) {
    return false
  }
  return hasString(value.error, 'code')
    && hasString(value.error, 'message')
    && Array.isArray(value.error.details)
}

export function isCourseSchedule(value: unknown): value is CourseSchedule {
  if (!isRecord(value)
    || !hasNumber(value, 'weekday')
    || !hasNumber(value, 'start_minute')
    || !hasNumber(value, 'end_minute')
    || !hasString(value, 'room')) {
    return false
  }
  return value.weekday >= 1
    && value.weekday <= 7
    && value.start_minute >= 0
    && value.start_minute < value.end_minute
    && value.end_minute <= 1440
}

export function isCourseSummary(value: unknown): value is CourseSummary {
  if (!isRecord(value)
    || !hasString(value, 'id')
    || !hasString(value, 'code')
    || !hasString(value, 'name')
    || typeof value.teacher_name !== 'string'
    || !hasNumber(value, 'credits')
    || !hasNumber(value, 'capacity')
    || !hasNumber(value, 'enrolled_count')
    || !hasNumber(value, 'waitlist_count')
    || !isCourseStatus(value.status)
    || !Array.isArray(value.schedules)
    || !Array.isArray(value.prerequisites)) {
    return false
  }
  return value.credits > 0
    && value.capacity > 0
    && value.enrolled_count >= 0
    && value.waitlist_count >= 0
    && value.schedules.every(isCourseSchedule)
    && value.prerequisites.every(item => typeof item === 'string')
}

export function safeCourseList(value: unknown): CourseSummary[] {
  return Array.isArray(value) ? value.filter(isCourseSummary) : []
}
