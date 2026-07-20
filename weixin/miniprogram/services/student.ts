import { isCourseSchedule, isRecord, safeCourseList } from '../domain/guards'
import type {
  AuditRecord,
  CourseSummary,
  EnrollmentRecord,
  RecommendationRequest,
  RecommendationSession,
  ScheduleItem,
  ScheduleSnapshot,
  WaitlistRecord,
} from '../domain/types'
import { createIdempotencyKey, type HttpResult } from './http'
import { apiClient } from './runtime'

export interface CourseFilters {
  keyword?: string
  status?: string
  weekday?: number
  period?: number
}

export interface StudentClient {
  request<T>(path: string, options?: {
    method?: 'GET' | 'POST'
    data?: unknown
    idempotencyKey?: string
  }): Promise<HttpResult<T>>
}

function query(filters: CourseFilters): string {
  const params: string[] = []
  if (filters.keyword?.trim()) params.push('keyword=' + encodeURIComponent(filters.keyword.trim()))
  if (filters.status) params.push('status=' + encodeURIComponent(filters.status))
  const value = params.join('&')
  return value ? '?' + value : ''
}

function toCourseResult(result: HttpResult<unknown>): HttpResult<CourseSummary[]> {
  return { ...result, data: safeCourseList(result.data) }
}

function scheduleItems(value: unknown): ScheduleItem[] {
  if (!Array.isArray(value)) return []
  return value.flatMap(item => {
    if (!isRecord(item)) return []
    if (typeof item.course_id === 'string'
      && (item.status === 'ENROLLED' || item.status === 'CONFLICT_REVIEW')
      && isCourseSchedule(item)) {
      return [item as unknown as ScheduleItem]
    }
    if (typeof item.id !== 'string' || !Array.isArray(item.schedules)) return []
    return item.schedules.filter(isCourseSchedule).map(schedule => ({
      course_id: item.id as string,
      course_code: typeof item.code === 'string' ? item.code : undefined,
      course_name: typeof item.name === 'string' ? item.name : undefined,
      teacher_name: typeof item.teacher_name === 'string' ? item.teacher_name : undefined,
      status: 'ENROLLED' as const,
      ...schedule,
    }))
  })
}

export function createStudentService(client: StudentClient) {
  return {
    async listCourses(filters: CourseFilters = {}): Promise<HttpResult<CourseSummary[]>> {
      const result = await client.request<unknown>('/courses' + query(filters))
      return toCourseResult(result)
    },

    async getCourse(courseId: string): Promise<HttpResult<CourseSummary>> {
      return client.request<CourseSummary>('/courses/' + encodeURIComponent(courseId))
    },

    async createRecommendations(payload: RecommendationRequest): Promise<HttpResult<RecommendationSession>> {
      return client.request<RecommendationSession>('/students/me/recommendations', {
        method: 'POST',
        data: { goals: payload.goals, preferences: payload.preferences },
        idempotencyKey: createIdempotencyKey('recommendation'),
      })
    },

    async getRecommendation(sessionId: string): Promise<HttpResult<RecommendationSession>> {
      return client.request<RecommendationSession>('/students/me/recommendations/' + encodeURIComponent(sessionId))
    },

    async requestEnrollment(courseId: string, type: 'ENROLL' | 'WAITLIST' | 'DROP', idempotencyKey?: string) {
      return client.request<unknown>('/students/me/enrollment-requests', {
        method: 'POST',
        data: { course_id: courseId, type },
        idempotencyKey: idempotencyKey ?? createIdempotencyKey('enrollment'),
      })
    },

    async listEnrollments(): Promise<HttpResult<EnrollmentRecord[]>> {
      return client.request<EnrollmentRecord[]>('/students/me/enrollments')
    },

    async listWaitlists(): Promise<HttpResult<WaitlistRecord[]>> {
      return client.request<WaitlistRecord[]>('/students/me/waitlists')
    },

    async getSchedule(): Promise<HttpResult<ScheduleSnapshot>> {
      const result = await client.request<unknown>('/students/me/schedule')
      if (Array.isArray(result.data)) {
        return { ...result, data: { courses: scheduleItems(result.data) } }
      }
      if (isRecord(result.data) && Array.isArray(result.data.courses)) {
        return {
          ...result,
          data: {
            courses: scheduleItems(result.data.courses),
            generated_at: typeof result.data.generated_at === 'string' ? result.data.generated_at : undefined,
            cache_backend: typeof result.data.cache_backend === 'string' ? result.data.cache_backend : undefined,
          },
        }
      }
      return { ...result, data: { courses: [] } }
    },

    async listAuditLogs(): Promise<HttpResult<AuditRecord[]>> {
      return client.request<AuditRecord[]>('/students/me/audit-logs')
    },
  }
}

export const studentService = createStudentService(apiClient)

export function filterCourseList(courses: CourseSummary[], filters: CourseFilters): CourseSummary[] {
  const keyword = (filters.keyword ?? '').trim().toLowerCase()
  return courses.filter(course => {
    if (keyword && ![course.code, course.name, course.teacher_name].some(value => value.toLowerCase().includes(keyword))) {
      return false
    }
    if (filters.status && course.status !== filters.status) return false
    if (filters.weekday && !course.schedules.some(schedule => schedule.weekday === filters.weekday)) return false
    if (filters.period && !course.schedules.some(schedule => Math.floor((schedule.start_minute - 480) / 60) + 1 === filters.period)) return false
    return true
  })
}

export function hasExpectedRecommendationRequest(value: unknown): boolean {
  return isRecord(value)
    && typeof value.goals === 'string'
    && Array.isArray(value.preferences)
    && Object.keys(value).every(key => key === 'goals' || key === 'preferences')
}
