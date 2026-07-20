export const ROLES = ['STUDENT', 'ACADEMIC'] as const
export type Role = typeof ROLES[number]

export const COURSE_STATUSES = ['OPEN', 'PENDING_APPROVAL', 'CLOSED', 'CANCELLED'] as const
export type CourseStatus = typeof COURSE_STATUSES[number]

export const ENROLLMENT_STATUSES = ['ENROLLED', 'CONFLICT_REVIEW', 'DROPPED', 'CANCELLED_BY_ADMIN'] as const
export type EnrollmentStatus = typeof ENROLLMENT_STATUSES[number]

export const WAITLIST_STATUSES = ['WAITING', 'PROMOTED', 'SKIPPED', 'REMOVED', 'CLOSED'] as const
export type WaitlistStatus = typeof WAITLIST_STATUSES[number]

export const RECOMMENDATION_STATUSES = ['PENDING', 'COMPLETED', 'FALLBACK'] as const
export type RecommendationStatus = typeof RECOMMENDATION_STATUSES[number]

export const RUN_STATUSES = ['PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED'] as const
export type RunStatus = typeof RUN_STATUSES[number]

export const APPROVAL_STATUSES = ['PENDING', 'APPROVED', 'REJECTED'] as const
export type ApprovalStatus = typeof APPROVAL_STATUSES[number]

export type EnrollmentRequestType = 'ENROLL' | 'WAITLIST' | 'DROP'

export interface ResponseMeta {
  request_id: string
  page?: number
  page_size?: number
  total?: number
}

export interface SuccessEnvelope<T> {
  data: T
  meta: ResponseMeta
}

export interface ApiErrorDetail {
  field?: string
  reason?: string
  [key: string]: unknown
}

export interface ApiErrorBody {
  code: string
  message: string
  details: ApiErrorDetail[]
}

export interface ErrorEnvelope {
  error: ApiErrorBody
  meta: ResponseMeta
}

export interface UserSummary {
  id: string
  username: string
  role: Role
  student_no?: string
  major?: string
  grade?: number
}

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  user: UserSummary
}

export interface CourseSchedule {
  weekday: number
  start_minute: number
  end_minute: number
  room: string
}

export interface CourseSummary {
  id: string
  code: string
  name: string
  teacher_name: string
  credits: number
  capacity: number
  enrolled_count: number
  waitlist_count: number
  status: CourseStatus
  schedules: CourseSchedule[]
  prerequisites: string[]
  version?: number
}

export type CourseOperationType = 'CREATE' | 'UPDATE' | 'CANCEL'

export interface CourseOperationRecord {
  id: string
  operation: CourseOperationType
  course_id?: string | null
  requester_id: string
  reviewer_id?: string | null
  status: ApprovalStatus
  payload: Record<string, unknown>
  comment?: string | null
  reason?: string | null
  idempotency_key?: string | null
  created_at?: string
  updated_at?: string
}

export interface ExceptionApprovalRecord {
  id: string
  request_id?: string | null
  enrollment_id?: string | null
  student_id: string
  course_id: string
  status: ApprovalStatus
  rule_violations: string[]
  waived_rules: string[]
  reviewer_id?: string | null
  comment?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface RuleViolation {
  code: string
  message: string
  blocking: boolean
}

export interface EligibilitySnapshot {
  eligible: boolean
  decision: string
  violations: RuleViolation[]
  warnings: string[]
  checked_at: string
}

export interface RecommendationItem {
  course_id: string
  rank: number
  reasons: string[]
  uncertainties: string[]
  eligibility: EligibilitySnapshot
}

export interface RecommendationSession {
  id: string
  status: RecommendationStatus
  items: RecommendationItem[]
}

export interface RecommendationRequest {
  goals: string
  preferences: string[]
}

export interface EnrollmentRecord {
  id: string
  student_id: string
  course_id: string
  status: EnrollmentStatus
  created_at?: string
}

export interface WaitlistRecord {
  id: string
  student_id: string
  course_id: string
  status: WaitlistStatus
  position?: number
  joined_at?: string
  reason_code?: string
}

export interface ScheduleItem {
  course_id: string
  course_code?: string
  course_name?: string
  teacher_name?: string
  status: 'ENROLLED' | 'CONFLICT_REVIEW'
  weekday: number
  start_minute: number
  end_minute: number
  room: string
}

export interface ScheduleSnapshot {
  courses: ScheduleItem[]
  generated_at?: string
  cache_backend?: string
}

export interface RecalculationSummary {
  checked: number
  promoted: number
  skipped: number
  conflicts: number
  waiting: number
  errors: number
}

export interface RecalculationResult {
  entity_type: 'COURSE' | 'ENROLLMENT' | 'WAITLIST'
  entity_id: string
  student_id?: string | null
  old_status?: string | null
  new_status?: string | null
  reason_code: string
  details: Record<string, unknown>
  occurred_at?: string | null
}

export interface RecalculationRun {
  id: string
  course_id: string
  trigger_type: 'EXPAND' | 'RESCHEDULE' | 'CANCEL' | 'MANUAL' | 'COURSE_UPDATE'
  operator_id?: string | null
  status: RunStatus
  summary: RecalculationSummary
  results: RecalculationResult[]
  started_at?: string | null
  finished_at?: string | null
  error?: ApiErrorBody | null
}

export interface ApprovalRecord {
  id: string
  request_id?: string | null
  enrollment_id?: string | null
  student_id: string
  course_id: string
  status: ApprovalStatus
  rule_violations: string[]
  waived_rules: string[]
  reviewer_id?: string | null
  comment?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface AuditRecord {
  id: string
  actor_id: string
  subject_student_id?: string | null
  actor_role: Role
  action: string
  resource_type: string
  resource_id: string
  before_json: Record<string, unknown>
  after_json: Record<string, unknown>
  reason?: string | null
  run_id?: string | null
  request_id: string
  created_at: string
}

export interface PageState<T> {
  phase: 'idle' | 'loading' | 'empty' | 'data' | 'error'
  data: T
  message: string
  stale: boolean
}

export const STATUS_LABELS: Readonly<Record<string, string>> = {
  OPEN: '开放',
  PENDING_APPROVAL: '待审批',
  CLOSED: '已关闭',
  CANCELLED: '已取消',
  ENROLLED: '已选',
  CONFLICT_REVIEW: '冲突复核',
  DROPPED: '已退课',
  CANCELLED_BY_ADMIN: '教务取消',
  WAITING: '候补中',
  PROMOTED: '已补位',
  SKIPPED: '本轮跳过',
  REMOVED: '已退出候补',
  PENDING: '处理中',
  COMPLETED: '推荐完成',
  FALLBACK: '规则兜底',
  RUNNING: '运行中',
  SUCCEEDED: '已完成',
  FAILED: '失败',
  APPROVED: '已批准',
  REJECTED: '已拒绝',
}

export const ERROR_MESSAGES: Readonly<Record<string, string>> = {
  UNAUTHORIZED: '登录已失效，请重新登录',
  INVALID_TOKEN: '登录已失效，请重新登录',
  FORBIDDEN: '当前账号无权执行此操作',
  COURSE_NOT_FOUND: '课程不存在或已被移除',
  RUN_NOT_FOUND: '重算批次不存在',
  APPROVAL_NOT_FOUND: '审批记录不存在',
  CAPACITY_FULL: '课程已满，可选择加入候补',
  DUPLICATE_ENROLLMENT: '请勿重复选课',
  DUPLICATE: '请勿重复选课或重复加入候补',
  CONFLICT: '课程时间与已选课程冲突，请刷新课表后调整',
  TIME_CONFLICT: '课程时间与已选课程冲突，请刷新课表后调整',
  PREREQUISITE_MISSING: '缺少课程先修条件，请先完成先修课程',
  COURSE_CLOSED: '课程当前不可选',
  COURSE_CANCELLED: '课程已取消，暂不可选',
  GRADE_NOT_MET: '当前年级不满足课程要求',
  MAJOR_NOT_MET: '当前专业不满足课程要求',
  EXCEPTION_REQUIRED: '该课程需要教务审批后才能选课',
  APPROVAL_RECHECK_FAILED: '数据已变化，请刷新后重试',
  CONCURRENT_MODIFICATION: '数据已变化，请刷新后重试',
  APPROVAL_RULE_NOT_ALLOWED: '所选规则不可豁免',
  VALIDATION_ERROR: '提交内容不符合要求',
  INTERNAL_ERROR: '服务暂时不可用，请稍后重试',
  SERVICE_UNAVAILABLE: '服务正在维护，请稍后重试',
  NETWORK_ERROR: '网络连接失败，请检查网络后重试',
  REQUEST_TIMEOUT: '请求超时，请稍后重试',
}
