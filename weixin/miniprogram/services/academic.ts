import type {
  ApprovalStatus,
  AuditRecord,
  CourseOperationRecord,
  CourseSummary,
  ExceptionApprovalRecord,
  RecalculationRun,
  RunStatus,
} from '../domain/types'
import { isRecord, safeCourseList } from '../domain/guards'
import { createIdempotencyKey, type HttpResult, type RequestOptions } from './http'
import { apiClient } from './runtime'

export interface AcademicClient {
  request<T>(path: string, options?: RequestOptions): Promise<HttpResult<T>>
}

export interface AdminCourseFilters {
  keyword?: string
  status?: string
  page?: number
  pageSize?: number
}

export interface CourseWritePayload {
  code: string
  name: string
  teacher_name: string
  credits: number
  capacity: number
  schedules: Array<{ weekday: number; start_minute: number; end_minute: number; room: string }>
  prerequisites: string[]
}

function query(filters: AdminCourseFilters): string {
  const params: string[] = []
  if (filters.keyword?.trim()) params.push('keyword=' + encodeURIComponent(filters.keyword.trim()))
  if (filters.status) params.push('status=' + encodeURIComponent(filters.status))
  if (filters.page) params.push('page=' + encodeURIComponent(String(filters.page)))
  if (filters.pageSize) params.push('page_size=' + encodeURIComponent(String(filters.pageSize)))
  const value = params.join('&')
  return value ? '?' + value : ''
}

function asList<T>(result: HttpResult<unknown>): HttpResult<T[]> {
  return { ...result, data: Array.isArray(result.data) ? result.data as T[] : [] }
}

function idempotency(scope: string, key?: string): string {
  return key ?? createIdempotencyKey(scope)
}

export function createAcademicService(client: AcademicClient) {
  return {
    async listCourses(filters: AdminCourseFilters = {}): Promise<HttpResult<CourseSummary[]>> {
      const result = await client.request<unknown>('/admin/courses' + query(filters))
      return { ...result, data: safeCourseList(result.data) }
    },

    async createCourse(payload: CourseWritePayload, key?: string) {
      return client.request<unknown>('/admin/courses', {
        method: 'POST',
        data: payload,
        idempotencyKey: idempotency('course-create', key),
      })
    },

    async updateCourse(courseId: string, payload: CourseWritePayload, expectedVersion?: number, key?: string) {
      const suffix = expectedVersion === undefined ? '' : '?expected_version=' + encodeURIComponent(String(expectedVersion))
      return client.request<unknown>('/admin/courses/' + encodeURIComponent(courseId) + suffix, {
        method: 'PATCH',
        data: payload,
        idempotencyKey: idempotency('course-update', key),
      })
    },

    async expandCourse(courseId: string, capacityDelta: number, expectedVersion?: number, key?: string) {
      const suffix = expectedVersion === undefined ? '' : '?expected_version=' + encodeURIComponent(String(expectedVersion))
      return client.request<unknown>('/admin/courses/' + encodeURIComponent(courseId) + '/expand' + suffix, {
        method: 'POST',
        data: { capacity_delta: capacityDelta },
        idempotencyKey: idempotency('course-expand', key),
      })
    },

    async rescheduleCourse(courseId: string, schedules: CourseWritePayload['schedules'], expectedVersion?: number, key?: string) {
      const suffix = expectedVersion === undefined ? '' : '?expected_version=' + encodeURIComponent(String(expectedVersion))
      return client.request<unknown>('/admin/courses/' + encodeURIComponent(courseId) + '/reschedule' + suffix, {
        method: 'POST',
        data: { schedules },
        idempotencyKey: idempotency('course-reschedule', key),
      })
    },

    async cancelCourse(courseId: string, reason: string, expectedVersion?: number, key?: string) {
      const suffix = expectedVersion === undefined ? '' : '?expected_version=' + encodeURIComponent(String(expectedVersion))
      return client.request<unknown>('/admin/courses/' + encodeURIComponent(courseId) + '/cancel' + suffix, {
        method: 'POST',
        data: { reason },
        idempotencyKey: idempotency('course-cancel', key),
      })
    },

    async startRecalculation(courseId: string, expectedVersion?: number, key?: string): Promise<HttpResult<RecalculationRun>> {
      const suffix = expectedVersion === undefined ? '' : '?expected_version=' + encodeURIComponent(String(expectedVersion))
      return client.request<RecalculationRun>('/admin/courses/' + encodeURIComponent(courseId) + '/recalculate' + suffix, {
        method: 'POST',
        idempotencyKey: idempotency('recalculation', key),
      })
    },

    async getRun(runId: string): Promise<HttpResult<RecalculationRun>> {
      return client.request<RecalculationRun>('/admin/recalculation-runs/' + encodeURIComponent(runId))
    },

    async listExceptionApprovals(status?: ApprovalStatus): Promise<HttpResult<ExceptionApprovalRecord[]>> {
      const result = await client.request<unknown>('/admin/exception-approvals' + query({ status }))
      return asList<ExceptionApprovalRecord>(result)
    },

    async decideException(approvalId: string, decision: 'approve' | 'reject', comment: string) {
      return client.request<unknown>('/admin/exception-approvals/' + encodeURIComponent(approvalId) + '/' + decision, {
        method: 'POST',
        data: { comment, waived_rules: [] },
        idempotencyKey: idempotency('exception-' + decision),
      })
    },

    async listCourseOperations(status?: ApprovalStatus): Promise<HttpResult<CourseOperationRecord[]>> {
      const result = await client.request<unknown>('/admin/course-operation-approvals' + query({ status }))
      return asList<CourseOperationRecord>(result)
    },

    async decideCourseOperation(operationId: string, decision: 'approve' | 'reject', comment: string) {
      return client.request<unknown>('/admin/course-operation-approvals/' + encodeURIComponent(operationId) + '/' + decision, {
        method: 'POST',
        data: { comment, waived_rules: [] },
        idempotencyKey: idempotency('course-operation-' + decision),
      })
    },

    async listAuditLogs(filters: { courseId?: string; runId?: string; action?: string } = {}): Promise<HttpResult<AuditRecord[]>> {
      const params: string[] = []
      if (filters.courseId) params.push('course_id=' + encodeURIComponent(filters.courseId))
      if (filters.runId) params.push('run_id=' + encodeURIComponent(filters.runId))
      if (filters.action) params.push('action=' + encodeURIComponent(filters.action))
      const suffix = params.length ? '?' + params.join('&') : ''
      const result = await client.request<unknown>('/admin/audit-logs' + suffix)
      return asList<AuditRecord>(result)
    },
  }
}

export const academicService = createAcademicService(apiClient)

export function isTerminalRun(status: unknown): status is Exclude<RunStatus, 'PENDING' | 'RUNNING'> {
  return status === 'SUCCEEDED' || status === 'FAILED'
}

export async function pollRun(
  getRun: (runId: string) => Promise<HttpResult<RecalculationRun>>,
  runId: string,
  options: { attempts?: number; intervalMs?: number; sleep?: (ms: number) => Promise<void> } = {},
): Promise<HttpResult<RecalculationRun>> {
  const attempts = Math.max(1, options.attempts ?? 6)
  const intervalMs = Math.max(0, options.intervalMs ?? 1000)
  const sleep = options.sleep ?? ((ms: number) => new Promise(resolve => setTimeout(resolve, ms)))
  let last = await getRun(runId)
  for (let index = 1; index < attempts && !isTerminalRun(last.data.status); index += 1) {
    await sleep(intervalMs)
    last = await getRun(runId)
  }
  return last
}

export function readRunId(value: unknown): string | undefined {
  if (!isRecord(value)) return undefined
  const run = isRecord(value.run) ? value.run : value
  return typeof run.id === 'string' ? run.id : undefined
}
