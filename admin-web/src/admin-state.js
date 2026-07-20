import {
  COURSE_PERIOD_OPTIONS,
  COURSE_PERIODS,
  WEEKDAY_OPTIONS,
  formatMinutes,
  formatScheduleTime,
  minutesToPeriod as canonicalMinutesToPeriod,
  periodToMinutes as canonicalPeriodToMinutes,
} from './course-time.js'

export const TERMINAL_RUN_STATUSES = new Set(['SUCCEEDED', 'FAILED'])
export const WAIVABLE_RULES = new Set(['CONFLICT', 'TIME_CONFLICT', 'PREREQUISITE_MISSING'])

const ERROR_MESSAGES = {
  UNAUTHORIZED: '登录已失效，请重新登录',
  FORBIDDEN: '当前账号没有教务操作权限',
  COURSE_NOT_FOUND: '课程不存在，请刷新课程列表',
  COURSE_ALREADY_EXISTS: '课程编号已存在，请更换后再提交',
  PREREQUISITE_NOT_FOUND: '先修课程编号不存在，请检查后再提交',
  INVALID_COURSE: '请完整填写课程基础信息',
  RUN_NOT_FOUND: '重算批次不存在或已失效',
  APPROVAL_NOT_FOUND: '审批记录不存在，请刷新审批队列',
  COURSE_OPERATION_NOT_FOUND: '课程操作申请不存在，请刷新审批中心',
  COURSE_OPERATION_NOT_PENDING: '课程操作申请已处理，请刷新审批中心',
  COURSE_OPERATION_PENDING: '该课程已有操作在审核，请先处理现有申请',
  RUN_ALREADY_ACTIVE: '该课程已有重算任务，请查看现有批次',
  CONCURRENT_MODIFICATION: '课程已被其他操作更新，请刷新后重试',
  COURSE_CANCELLED: '课程已取消，不能继续操作',
  COURSE_ALREADY_CANCELLED: '课程已经取消，请刷新列表',
  INVALID_CAPACITY_DELTA: '扩容量必须为正整数',
  INVALID_SCHEDULE: '课程时间不合法或存在重叠',
  EMPTY_REASON: '请填写取消原因',
  EMPTY_COMMENT: '请填写审批意见',
  APPROVAL_RECHECK_FAILED: '审批重查未通过，记录仍保持待审',
  APPROVAL_RULE_NOT_ALLOWED: '包含不可豁免规则，未提交审批',
  INVALID_TIME_RANGE: '审计开始时间不能晚于结束时间',
}

export function isTerminalRun(status) {
  return TERMINAL_RUN_STATUSES.has(status)
}

export function preserveServerResultOrder(results) {
  return Array.isArray(results) ? [...results] : []
}

export function allowedWaivedRules(violations) {
  return (violations || []).filter((rule) => WAIVABLE_RULES.has(rule))
}

export function validateSchedule(schedule) {
  const weekday = Number(schedule?.weekday)
  const start = Number(schedule?.start_minute)
  const end = Number(schedule?.end_minute)
  if (!Number.isInteger(weekday) || weekday < 1 || weekday > 7) return '星期必须为 1～7'
  if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end > 1440 || start >= end) return '开始时间必须早于结束时间'
  return ''
}

export function validateRequiredText(value, fieldName) {
  return String(value || '').trim() ? '' : `请填写${fieldName}`
}

export const WEEKDAY_LABELS = WEEKDAY_OPTIONS.map(item => item.label.slice(1))
export { COURSE_PERIOD_OPTIONS, COURSE_PERIODS, formatMinutes }

export function periodToMinutes(period) {
  return canonicalPeriodToMinutes(period)
}

export function minutesToPeriod(minutes) {
  return canonicalMinutesToPeriod(minutes)
}

export function formatScheduleText(schedule) {
  if (!schedule) return '未安排课表'
  const weekday = WEEKDAY_LABELS[(Number(schedule.weekday) || 1) - 1] || '?'
  return `周${weekday} ${formatScheduleTime(schedule)} · ${schedule.room || '待定'}`
}

export function userMessageForError(error) {
  if (error?.code && ERROR_MESSAGES[error.code]) return ERROR_MESSAGES[error.code]
  const status = error?.response?.status
  if (status === 401) return ERROR_MESSAGES.UNAUTHORIZED
  if (status === 403) return ERROR_MESSAGES.FORBIDDEN
  if (status >= 500) return '服务暂时不可用，请稍后重试'
  return error?.message || '请求失败'
}

export function isCourseCodeConflict(error) {
  return error?.code === 'COURSE_ALREADY_EXISTS'
}

export function isCourseEditorError(error) {
  return ['COURSE_ALREADY_EXISTS', 'PREREQUISITE_NOT_FOUND', 'INVALID_COURSE', 'INVALID_SCHEDULE'].includes(error?.code)
}

function sensitiveKey(key) {
  const normalized = String(key).toLowerCase().replaceAll('-', '_')
  return ['authorization', 'password', 'password_hash', 'api_key', 'access_token', 'refresh_token', 'client_secret', 'jwt_secret', 'deepseek_api_key'].includes(normalized)
    || normalized.endsWith('_token')
    || normalized.endsWith('_secret')
}

export function redactAuditSnapshot(value) {
  if (Array.isArray(value)) return value.map(redactAuditSnapshot)
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, sensitiveKey(key) ? '[REDACTED]' : redactAuditSnapshot(item)]))
  }
  return value
}

export function prettyJson(value) {
  return JSON.stringify(redactAuditSnapshot(value || {}), null, 2)
}

const AUDIT_ACTION_LABELS = {
  COURSE_CREATED: '新增课程',
  COURSE_UPDATED: '编辑课程',
  COURSE_EXPANDED: '课程扩容',
  COURSE_RESCHEDULED: '调整上课时间',
  COURSE_CANCELLED: '取消课程',
  COURSE_DELETED: '删除课程',
  COURSE_DELETED_BY_TEACHER: '教师删除课程',
  COURSE_OPERATION_SUBMITTED: '提交课程变更申请',
  COURSE_OPERATION_APPROVED: '批准课程变更',
  COURSE_OPERATION_REJECTED: '拒绝课程变更',
  WAITLIST_PROMOTED: '候补学生转为已选',
  WAITLIST_SKIPPED: '跳过候补学生',
  EXCEPTION_APPROVED: '批准例外申请',
  EXCEPTION_REJECTED: '拒绝例外申请',
  APPROVAL_APPROVED: '批准例外申请',
  APPROVAL_REJECTED: '拒绝例外申请',
  RECALCULATION_STARTED: '开始候补重算',
  RECOMMENDATION_CREATED: '生成课程推荐',
  ENROLLMENT_CREATED: '学生选课',
  ENROLLMENT_DROPPED: '学生退课',
  WAITLIST_JOINED: '学生加入候补',
  WAITLIST_REMOVED: '学生退出候补',
}

const RESOURCE_LABELS = {
  course: '课程',
  course_operation: '课程变更申请',
  enrollment: '选课记录',
  waitlist_entry: '候补记录',
  approval: '例外申请',
  exception_approval: '例外申请',
  recalculation_run: '候补重算批次',
  recommendation_session: '课程推荐记录',
  recommendation: '课程推荐记录',
}

const STATUS_LABELS = {
  OPEN: '开放', CANCELLED: '已取消', DELETED: '已删除', ENROLLED: '已选课',
  CONFLICT_REVIEW: '冲突复核中', CANCELLED_BY_ADMIN: '因教师删除课程而关闭',
  WAITING: '候补中', PROMOTED: '候补通过', SKIPPED: '已跳过', CLOSED: '已关闭',
  PENDING: '待处理', APPROVED: '已批准', REJECTED: '已拒绝',
}

const REASON_LABELS = {
  COURSE_CANCELLED: '课程已删除，相关选课或候补记录已关闭',
  TIME_CONFLICT: '与学生现有课程时间冲突',
  CONFLICT: '与学生现有课程冲突',
  PREREQUISITE_MISSING: '学生尚未满足先修课程要求',
  ELIGIBLE: '资格校验通过',
}

export function auditActionLabel(action) {
  return AUDIT_ACTION_LABELS[action] || '其他操作'
}

export function auditResourceLabel(resourceType) {
  return RESOURCE_LABELS[resourceType] || '其他记录'
}

function auditCourseName(audit, course = null) {
  for (const snapshot of [audit?.after_json, audit?.before_json]) {
    const payload = snapshot?.payload || snapshot || {}
    const name = payload.course_name || payload.name
    const code = payload.course_code || payload.code
    if (name && code) return `${code} ${name}`
    if (name || code) {
      const fallbackCode = code || course?.code
      const fallbackName = name || course?.name
      if (fallbackCode && fallbackName) return `${fallbackCode} ${fallbackName}`
      return String(name || code)
    }
  }
  if (course?.code && course?.name) return `${course.code} ${course.name}`
  return String(audit?.resource_id || '未知课程')
}

export function auditDescription(audit, course = null) {
  const action = audit?.action
  const courseName = auditCourseName(audit, course)
  if (action === 'COURSE_CREATED') return `新增课程《${courseName}》。`
  if (action === 'COURSE_UPDATED') return `已更新课程《${courseName}》的信息。`
  if (action === 'COURSE_EXPANDED') return `已为课程《${courseName}》扩容。`
  if (action === 'COURSE_RESCHEDULED') return `已调整课程《${courseName}》的上课时间。`
  if (['COURSE_CANCELLED', 'COURSE_DELETED'].includes(action)) return `已删除课程《${courseName}》。`
  if (action === 'COURSE_DELETED_BY_TEACHER') return `教师已删除课程《${courseName}》，学生记录已关闭。`
  if (action === 'WAITLIST_PROMOTED') return `学生 ${audit?.subject_student_id || '-'} 在课程《${courseName}》已候补通过。`
  if (action === 'WAITLIST_SKIPPED') return `学生 ${audit?.subject_student_id || '-'} 在课程《${courseName}》暂未候补通过。`
  if (action === 'COURSE_OPERATION_SUBMITTED') return `教师已提交课程《${courseName}》的变更申请，等待审批。`
  if (action === 'COURSE_OPERATION_APPROVED') return `课程《${courseName}》的变更申请已批准并生效。`
  if (action === 'COURSE_OPERATION_REJECTED') return `课程《${courseName}》的变更申请已被拒绝。`
  if (action === 'RECALCULATION_STARTED') return `已开始候补重算，批次编号为 ${audit?.resource_id || '-'}。`
  if (action === 'RECOMMENDATION_CREATED') return `学生 ${audit?.subject_student_id || audit?.actor_id || '-'} 已生成一份课程推荐。`
  if (action === 'ENROLLMENT_CREATED') return `学生 ${audit?.subject_student_id || '-'} 已选择课程《${courseName}》。`
  if (action === 'ENROLLMENT_DROPPED') return `学生 ${audit?.subject_student_id || '-'} 已退出课程《${courseName}》。`
  if (action === 'WAITLIST_JOINED') return `学生 ${audit?.subject_student_id || '-'} 已加入课程《${courseName}》候补。`
  if (action === 'WAITLIST_REMOVED') return `学生 ${audit?.subject_student_id || '-'} 已退出课程《${courseName}》候补。`
  const reason = String(audit?.reason || '').trim()
  return `${auditActionLabel(action)}：已更新${auditResourceLabel(audit?.resource_type)} ${audit?.resource_id || '-'}${reason ? `；说明：${reason}` : ''}`
}

export function auditChangeDescription(audit) {
  const before = redactAuditSnapshot(audit?.before_json || {})
  const after = redactAuditSnapshot(audit?.after_json || {})
  const changes = []
  const addChange = (label, oldValue, newValue, format = value => value) => {
    if (oldValue === undefined || newValue === undefined || JSON.stringify(oldValue) === JSON.stringify(newValue)) return
    changes.push(`${label}：${format(oldValue)} → ${format(newValue)}`)
  }
  addChange('课程名称', before.name || before.course_name, after.name || after.course_name)
  addChange('任课教师', before.teacher_name, after.teacher_name)
  addChange('课程学分', before.credits, after.credits, value => `${value} 学分`)
  addChange('课程容量', before.capacity, after.capacity, value => `${value} 人`)
  addChange('状态', before.status, after.status, value => STATUS_LABELS[value] || value)
  if (before.schedules !== undefined && after.schedules !== undefined && JSON.stringify(before.schedules) !== JSON.stringify(after.schedules)) changes.push('上课时间：已调整')
  if (!changes.length && audit?.reason) changes.push(`处理说明：${audit.reason}`)
  return changes.join('；') || '本次操作没有可展示的字段变化。'
}

export function describeCourseOperation(operation) {
  const payload = operation?.payload || {}
  const parts = []
  if (payload.code || payload.name) parts.push(`课程：${[payload.code, payload.name].filter(Boolean).join(' ')}`)
  if (payload.teacher_name) parts.push(`任课教师：${payload.teacher_name}`)
  if (payload.credits !== undefined) parts.push(`学分：${payload.credits}`)
  if (payload.capacity !== undefined) parts.push(`容量：${payload.capacity} 人`)
  if (Array.isArray(payload.schedules) && payload.schedules.length) parts.push(`上课时间：${payload.schedules.map(formatScheduleText).join('；')}`)
  if (Array.isArray(payload.prerequisites)) parts.push(`先修课程：${payload.prerequisites.length ? payload.prerequisites.join('、') : '无'}`)
  if (payload.reason) parts.push(`删除原因：${payload.reason}`)
  return parts.join('；') || '未提供更多课程变更信息。'
}

export function describeRunResult(result) {
  const reason = REASON_LABELS[result?.reason_code] || result?.reason_code || '未提供原因'
  const violations = Array.isArray(result?.details?.violations) ? result.details.violations.map(item => item.message || item.code || item).filter(Boolean) : []
  return violations.length ? `${reason}；${violations.join('；')}` : reason
}

export function courseImpactMessage(preview = {}) {
  const courseLabel = [preview.course_code, preview.course_name].filter(Boolean).join(' ') || preview.course_id || '课程'
  return `本次变更 ${courseLabel} · 课程已选人数 ${Number(preview.enrolled_count || 0)} 人 · 候补通过 ${Number(preview.promoted || 0)} 人 · 仍在候补 ${Number(preview.waiting || 0)} 人 · 修改时间后与学生已选课程时间冲突 ${Number(preview.conflicts || 0)} 人 · 错误操作 ${Number(preview.errors || 0)}。`
}

export function courseImpactDialogOptions() {
  return {
    confirmButtonText: '确认',
    cancelButtonText: '取消',
    type: 'warning',
    center: true,
    closeOnClickModal: false,
    distinguishCancelAndClose: true,
  }
}

export function statusTagType(status) {
  return {
    OPEN: 'success',
    PENDING_APPROVAL: 'warning',
    CANCELLED: 'danger',
    SUCCEEDED: 'success',
    FAILED: 'danger',
    RUNNING: 'warning',
    PENDING: 'info',
    APPROVED: 'success',
    REJECTED: 'danger',
    PROMOTED: 'success',
    SKIPPED: 'warning',
    WAITING: 'info',
    CLOSED: 'danger',
    ENROLLED: 'success',
    CONFLICT_REVIEW: 'warning',
    CANCELLED_BY_ADMIN: 'danger',
  }[status] || 'info'
}
