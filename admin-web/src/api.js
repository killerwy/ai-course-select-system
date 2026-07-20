import axios from 'axios'
import { parseAcademicHandoff } from './session-handoff.js'

const env = import.meta.env || {}
const useMock = env.VITE_USE_MOCK !== 'false'
const baseURL = env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
const client = axios.create({ baseURL, timeout: 8000 })
let accessToken = typeof window !== 'undefined' ? window.localStorage.getItem('academic_access_token') : null
let mockScenario = env.VITE_MOCK_SCENARIO || 'normal'

const INITIAL_COURSES = [
  { id: 'course-101', code: 'CS101', name: '程序设计基础', teacher_name: '王老师', capacity: 2, enrolled_count: 1, waitlist_count: 0, status: 'OPEN', schedules: [{ weekday: 1, start_minute: 480, end_minute: 570, room: 'A101' }] },
  { id: 'course-201', code: 'AI201', name: '人工智能导论', teacher_name: '李老师', capacity: 1, enrolled_count: 1, waitlist_count: 2, status: 'OPEN', schedules: [{ weekday: 1, start_minute: 480, end_minute: 570, room: 'B201' }] },
  { id: 'course-301', code: 'SE301', name: '软件工程实践', teacher_name: '周老师', capacity: 3, enrolled_count: 0, waitlist_count: 1, status: 'OPEN', schedules: [{ weekday: 3, start_minute: 600, end_minute: 690, room: 'C301' }] },
]

const INITIAL_APPROVALS = [
  { id: 'approval-mock-001', student_id: 'student-demo-001', course_id: 'course-201', status: 'PENDING', rule_violations: ['TIME_CONFLICT'], waived_rules: [], comment: null },
  { id: 'approval-mock-002', student_id: 'student-demo-002', course_id: 'course-301', status: 'REJECTED', rule_violations: ['PREREQUISITE_MISSING'], waived_rules: [], comment: '演示拒绝记录' },
]

const INITIAL_AUDITS = [
  { id: 'audit-mock-003', actor_id: 'academic-001', actor_role: 'ACADEMIC', subject_student_id: 'student-demo-002', action: 'WAITLIST_PROMOTED', resource_type: 'waitlist_entry', resource_id: 'wait-mock-002', before_json: { status: 'WAITING', course_id: 'course-201' }, after_json: { status: 'PROMOTED', course_id: 'course-201' }, reason: 'ELIGIBLE', run_id: 'run-mock-seed', request_id: 'mock-003', created_at: '2026-07-16T08:02:00Z' },
  { id: 'audit-mock-002', actor_id: 'academic-001', actor_role: 'ACADEMIC', subject_student_id: 'student-demo-001', action: 'WAITLIST_SKIPPED', resource_type: 'waitlist_entry', resource_id: 'wait-mock-001', before_json: { status: 'WAITING', course_id: 'course-201' }, after_json: { status: 'SKIPPED', course_id: 'course-201', authorization: '[REDACTED]' }, reason: 'TIME_CONFLICT', run_id: 'run-mock-seed', request_id: 'mock-002', created_at: '2026-07-16T08:01:00Z' },
  { id: 'audit-mock-001', actor_id: 'academic-001', actor_role: 'ACADEMIC', subject_student_id: null, action: 'COURSE_EXPANDED', resource_type: 'course', resource_id: 'course-201', before_json: { capacity: 1 }, after_json: { capacity: 2 }, reason: 'capacity +1', run_id: 'run-mock-seed', request_id: 'mock-001', created_at: '2026-07-16T08:00:00Z' },
]

let mockCourses = []
let mockApprovals = []
let mockCourseOperations = []
let mockAudits = []
const mockRuns = new Map()

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

function unwrap(payload) {
  return payload?.data ?? payload
}

export function idempotencyKey(prefix, value) {
  const prefixPart = String(prefix || 'request').replace(/[^a-zA-Z0-9_-]/g, '').slice(0, 16)
  const valuePart = String(value || 'item').replace(/[^a-zA-Z0-9_-]/g, '').slice(-24)
  const timestampPart = Date.now().toString(36)
  const entropyPart = Math.random().toString(16).slice(2, 10)
  return `${prefixPart}-${valuePart}-${timestampPart}-${entropyPart}`
}

function compactFilters(filters = {}) {
  return Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== '' && value !== null && value !== undefined))
}

function normalizeAuditFilters(filters = {}) {
  const result = compactFilters(filters)
  for (const key of ['from', 'to']) {
    if (result[key] && !/[zZ]|[+-]\d\d:\d\d$/.test(String(result[key]))) result[key] = `${result[key]}Z`
  }
  return result
}

function mockError(code, message, status = 500) {
  const error = new Error(message)
  error.code = code
  error.details = []
  error.response = { status, data: { error: { code, message, details: [] } } }
  return error
}

function guardMock(scope) {
  if (mockScenario === 'network-error') throw mockError('NETWORK_ERROR', `${scope} mock network failure`, 503)
  if (mockScenario === 'forbidden') throw mockError('FORBIDDEN', 'mock academic access denied', 403)
  if (scope === 'approval' && mockScenario === 'approval-conflict') throw mockError('APPROVAL_RECHECK_FAILED', 'mock approval recheck failed', 409)
}

function mockResults(courseId, triggerType = 'MANUAL') {
  if (triggerType === 'CANCEL' && courseId === 'course-201') {
    return [
      { entity_type: 'ENROLLMENT', entity_id: 'enrollment-mock-201', student_id: 'student-demo-enrolled', old_status: 'ENROLLED', new_status: 'CANCELLED_BY_ADMIN', reason_code: 'COURSE_CANCELLED', details: {}, occurred_at: '2026-07-16T08:01:00Z' },
      { entity_type: 'WAITLIST', entity_id: 'wait-mock-001', student_id: 'student-demo-001', old_status: 'WAITING', new_status: 'CLOSED', reason_code: 'COURSE_CANCELLED', details: {}, occurred_at: '2026-07-16T08:02:00Z' },
      { entity_type: 'WAITLIST', entity_id: 'wait-mock-002', student_id: 'student-demo-002', old_status: 'WAITING', new_status: 'CLOSED', reason_code: 'COURSE_CANCELLED', details: {}, occurred_at: '2026-07-16T08:03:00Z' },
    ]
  }
  if (courseId === 'course-201') {
    return [
      { entity_type: 'WAITLIST', entity_id: 'wait-mock-001', student_id: 'student-demo-001', old_status: 'WAITING', new_status: 'SKIPPED', reason_code: 'TIME_CONFLICT', details: { position_at_start: 1, message: '与最新课表冲突' }, occurred_at: '2026-07-16T08:01:00Z' },
      { entity_type: 'WAITLIST', entity_id: 'wait-mock-002', student_id: 'student-demo-002', old_status: 'WAITING', new_status: 'PROMOTED', reason_code: 'ELIGIBLE', details: { position_at_start: 2 }, occurred_at: '2026-07-16T08:02:00Z' },
    ]
  }
  if (courseId === 'course-301') {
    return [{ entity_type: 'WAITLIST', entity_id: 'wait-mock-003', student_id: 'student-demo-003', old_status: 'WAITING', new_status: 'WAITING', reason_code: 'CAPACITY_FULL', details: { position_at_start: 1 }, occurred_at: '2026-07-16T08:03:00Z' }]
  }
  return []
}

function createMockRun(courseId, triggerType, { terminal = 'SUCCEEDED', synchronous = false } = {}) {
  const results = mockResults(courseId, triggerType)
  const run = {
    id: idempotencyKey(`run-mock-${triggerType.toLowerCase()}`, courseId),
    course_id: courseId,
    trigger_type: triggerType,
    status: synchronous ? terminal : 'PENDING',
    summary: {
      checked: results.length,
      promoted: results.filter((item) => item.new_status === 'PROMOTED').length,
      skipped: results.filter((item) => item.new_status === 'SKIPPED').length,
      waiting: results.filter((item) => item.new_status === 'WAITING').length,
      conflicts: 0,
      errors: terminal === 'FAILED' ? 1 : 0,
    },
    results,
    error: terminal === 'FAILED' ? { code: 'RECALCULATION_FAILED', message: 'mock task failure', details: [] } : null,
  }
  mockRuns.set(run.id, { run, polls: synchronous ? 2 : 0, terminal })
  return clone(run)
}

function addMockAudit({ action, resourceType, resourceId, courseId, runId, reason, subjectStudentId = null, before = {}, after = {} }) {
  mockAudits.unshift({
    id: idempotencyKey('audit-mock', resourceId),
    actor_id: 'academic-001',
    actor_role: 'ACADEMIC',
    subject_student_id: subjectStudentId,
    action,
    resource_type: resourceType,
    resource_id: resourceId,
    before_json: { ...before, course_id: courseId },
    after_json: { ...after, course_id: courseId },
    reason,
    run_id: runId,
    request_id: `mock:${runId || resourceId}`,
    created_at: new Date().toISOString(),
  })
}

function createMockCourseOperation(operation, courseId, payload) {
  const record = {
    id: idempotencyKey('course-operation', courseId || payload.code),
    operation,
    course_id: courseId,
    requester_id: 'academic-001',
    reviewer_id: null,
    status: 'PENDING',
    payload: clone(payload),
    reason: payload.reason || null,
    comment: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }
  mockCourseOperations.unshift(record)
  addMockAudit({ action: 'COURSE_OPERATION_SUBMITTED', resourceType: 'course_operation', resourceId: record.id, courseId: courseId || record.id, reason: 'course operation submitted', after: record })
  return clone(record)
}

function rememberToken(token) {
  accessToken = token
  if (typeof window !== 'undefined') window.localStorage.setItem('academic_access_token', token)
}

export function consumeAcademicHandoff() {
  if (typeof window === 'undefined') return false
  const handoff = parseAcademicHandoff(window.location.hash)
  if (!handoff) return false
  rememberToken(handoff.accessToken)
  window.history.replaceState(null, document.title, `${window.location.pathname}${window.location.search}`)
  return true
}

export function logoutAcademic() {
  accessToken = null
  if (typeof window !== 'undefined') window.localStorage.removeItem('academic_access_token')
}

export function hasAcademicSession() {
  return Boolean(accessToken)
}

function authenticationError(message = '请先登录教务账号') {
  const error = new Error(message)
  error.code = 'UNAUTHORIZED'
  error.response = { status: 401, data: { detail: message } }
  return error
}

export function isAuthenticationError(error) {
  return error?.code === 'UNAUTHORIZED' || error?.response?.status === 401
}

export async function loginAcademic(username, password) {
  if (!String(username || '').trim() || !String(password || '')) throw authenticationError('请输入用户名和密码')
  if (useMock) {
    const result = { access_token: 'mock-academic-token', token_type: 'bearer', user: { id: 'academic-001', username, role: 'ACADEMIC' } }
    rememberToken(result.access_token)
    return result
  }
  try {
    const { data } = await client.post('/auth/login', { username: String(username).trim(), password: String(password) })
    if (!data?.access_token || data?.user?.role !== 'ACADEMIC') throw authenticationError('该账号没有教务权限')
    rememberToken(data.access_token)
    return data
  } catch (error) {
    logoutAcademic()
    handleError(error)
  }
}

export async function restoreAcademicSession() {
  if (useMock) {
    if (!accessToken) throw authenticationError()
    return { id: 'academic-001', username: 'academic', role: 'ACADEMIC' }
  }
  if (!accessToken) throw authenticationError()
  try {
    const { data } = await client.get('/me', { headers: { Authorization: `Bearer ${accessToken}` } })
    const user = unwrap(data)
    if (user?.role !== 'ACADEMIC') throw authenticationError('该账号没有教务权限')
    return user
  } catch (error) {
    logoutAcademic()
    handleError(error)
  }
}

async function ensureToken() {
  if (!accessToken) throw authenticationError()
  return accessToken
}

async function headers(extra = {}) {
  const token = await ensureToken()
  return { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...extra }
}

function handleError(error) {
  const payload = error?.response?.data
  const detail = payload?.error?.message || payload?.detail || error?.message || '请求失败'
  const wrapped = new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  if (error?.response?.status === 401) logoutAcademic()
  wrapped.code = payload?.error?.code || (error?.response?.status === 401 ? 'UNAUTHORIZED' : error?.code)
  wrapped.details = payload?.error?.details || error?.details || []
  wrapped.response = error?.response
  throw wrapped
}

export function resetMockState() {
  mockCourses = clone(INITIAL_COURSES)
  mockApprovals = clone(INITIAL_APPROVALS)
  mockCourseOperations = []
  mockAudits = clone(INITIAL_AUDITS)
  mockRuns.clear()
}

export function configureMockScenario(scenario = 'normal') {
  mockScenario = scenario
  resetMockState()
}

resetMockState()

export async function listCourses(filters = {}) {
  if (useMock) {
    guardMock('courses')
    if (mockScenario === 'empty') return []
    const keyword = String(filters.keyword || '').toLowerCase()
    const courses = clone(mockCourses.filter((course) => (!keyword || `${course.code} ${course.name}`.toLowerCase().includes(keyword))))
    const pending = mockCourseOperations.filter((item) => item.status === 'PENDING')
    for (const operation of pending) {
      const payload = operation.payload || {}
      if (operation.operation === 'CREATE') {
        courses.push({ id: `pending-${operation.id}`, code: payload.code, name: payload.name, teacher_name: payload.teacher_name, credits: payload.credits, capacity: payload.capacity, enrolled_count: 0, waitlist_count: 0, status: 'PENDING_APPROVAL', version: 0, schedules: clone(payload.schedules || []), prerequisites: clone(payload.prerequisites || []), pending_operation: clone(operation) })
      } else {
        const course = courses.find((item) => item.id === operation.course_id)
        if (!course) continue
        if (operation.operation === 'UPDATE') Object.assign(course, clone(payload))
        course.status = 'PENDING_APPROVAL'
        course.pending_operation = clone(operation)
      }
    }
    return courses.filter((course) => (!filters.status || course.status === filters.status) && (!keyword || `${course.code} ${course.name}`.toLowerCase().includes(keyword)))
  }
  try {
    const response = await client.get('/admin/courses', { params: compactFilters(filters), headers: await headers() })
    return unwrap(response.data) || []
  } catch (error) {
    handleError(error)
  }
}

export async function createCourse(payload) {
  if (useMock) {
    guardMock('courses')
    if (mockCourses.some((item) => item.code === payload.code)) throw mockError('COURSE_ALREADY_EXISTS', 'course code already exists', 409)
    return { course: null, operation: createMockCourseOperation('CREATE', null, payload), run: null, reused: false }
  }
  try {
    const response = await client.post('/admin/courses', payload, { headers: await headers({ 'Idempotency-Key': idempotencyKey('create-course', payload.code) }) })
    return unwrap(response.data)
  } catch (error) {
    handleError(error)
  }
}

export async function updateCourse(courseId, payload) {
  if (useMock) {
    guardMock('courses')
    const course = mockCourses.find((item) => item.id === courseId)
    if (!course) throw mockError('COURSE_NOT_FOUND', 'course not found', 404)
    if (mockCourses.some((item) => item.id !== courseId && item.code === payload.code)) throw mockError('COURSE_ALREADY_EXISTS', 'course code already exists', 409)
    return { course: null, operation: createMockCourseOperation('UPDATE', courseId, payload), run: null, reused: false }
  }
  try {
    const response = await client.patch(`/admin/courses/${courseId}`, payload, { headers: await headers({ 'Idempotency-Key': idempotencyKey('update-course', courseId) }) })
    return unwrap(response.data)
  } catch (error) {
    handleError(error)
  }
}

export async function expandCourse(courseId, capacityDelta = 1) {
  if (useMock) {
    guardMock('expand')
    if (!Number.isInteger(capacityDelta) || capacityDelta <= 0) throw mockError('INVALID_CAPACITY_DELTA', 'capacity delta must be positive', 422)
    const course = mockCourses.find((item) => item.id === courseId)
    if (!course) throw mockError('COURSE_NOT_FOUND', 'course not found', 404)
    const before = course.capacity
    course.capacity += capacityDelta
    const terminal = mockScenario === 'failed-run' ? 'FAILED' : 'SUCCEEDED'
    const run = createMockRun(courseId, 'EXPAND', { terminal })
    if (terminal === 'SUCCEEDED' && courseId === 'course-201') {
      course.enrolled_count += 1
      course.waitlist_count = 0
    }
    addMockAudit({ action: 'COURSE_EXPANDED', resourceType: 'course', resourceId: courseId, courseId, runId: run.id, reason: `capacity +${capacityDelta}`, before: { capacity: before }, after: { capacity: course.capacity } })
    return { course: clone(course), run, reused: false }
  }
  try {
    const response = await client.post(`/admin/courses/${courseId}/expand`, { capacity_delta: capacityDelta }, { headers: await headers({ 'Idempotency-Key': idempotencyKey('expand', courseId) }) })
    return unwrap(response.data)
  } catch (error) {
    handleError(error)
  }
}

export async function previewCourseChange(courseId, payload) {
  if (useMock) {
    guardMock('course-change-preview')
    const course = mockCourses.find((item) => item.id === courseId)
    if (!course) throw mockError('COURSE_NOT_FOUND', 'course not found', 404)
    const operation = payload?.operation
    const capacity = Number(payload?.capacity ?? course.capacity)
    const enrolled = Number(course.enrolled_count || 0)
    const waitingBefore = Number(course.waitlist_count || 0)
    const promoted = operation === 'CANCEL' ? 0 : Math.min(Math.max(capacity - enrolled, 0), waitingBefore)
    const scheduleChanged = Array.isArray(payload?.schedules) && JSON.stringify(payload.schedules) !== JSON.stringify(course.schedules || [])
    return {
      operation,
      course_id: course.id,
      course_code: course.code,
      course_name: course.name,
      enrolled_count: enrolled,
      promoted,
      waiting: operation === 'CANCEL' ? waitingBefore : Math.max(waitingBefore - promoted, 0),
      conflicts: scheduleChanged && course.id === 'course-201' ? 1 : 0,
      errors: 0,
    }
  }
  try {
    const response = await client.post(`/admin/courses/${courseId}/change-preview`, payload, { headers: await headers() })
    return unwrap(response.data)
  } catch (error) {
    handleError(error)
  }
}

export async function rescheduleCourse(courseId, schedules) {
  if (useMock) {
    guardMock('reschedule')
    const course = mockCourses.find((item) => item.id === courseId)
    if (!course) throw mockError('COURSE_NOT_FOUND', 'course not found', 404)
    const before = clone(course.schedules)
    course.schedules = clone(schedules)
    const run = createMockRun(courseId, 'RESCHEDULE', { terminal: mockScenario === 'failed-run' ? 'FAILED' : 'SUCCEEDED' })
    addMockAudit({ action: 'COURSE_RESCHEDULED', resourceType: 'course', resourceId: courseId, courseId, runId: run.id, reason: 'course schedules changed', before: { schedules: before }, after: { schedules } })
    return { course: clone(course), run, reused: false }
  }
  try {
    const response = await client.post(`/admin/courses/${courseId}/reschedule`, { schedules }, { headers: await headers({ 'Idempotency-Key': idempotencyKey('reschedule', courseId) }) })
    return unwrap(response.data)
  } catch (error) {
    handleError(error)
  }
}

export async function cancelCourse(courseId, reason) {
  if (useMock) {
    guardMock('cancel')
    const course = mockCourses.find((item) => item.id === courseId)
    if (!course) throw mockError('COURSE_NOT_FOUND', 'course not found', 404)
    if (!String(reason || '').trim()) throw mockError('EMPTY_REASON', 'reason is required', 422)
    return { course: null, operation: createMockCourseOperation('CANCEL', courseId, { reason }), run: null, reused: false }
  }
  try {
    const response = await client.post(`/admin/courses/${courseId}/cancel`, { reason }, { headers: await headers({ 'Idempotency-Key': idempotencyKey('cancel', courseId) }) })
    return unwrap(response.data)
  } catch (error) {
    handleError(error)
  }
}

export async function startRecalculation(courseId) {
  if (useMock) {
    guardMock('recalculation')
    if (!mockCourses.some((item) => item.id === courseId)) throw mockError('COURSE_NOT_FOUND', 'course not found', 404)
    return createMockRun(courseId, 'MANUAL', { terminal: mockScenario === 'failed-run' ? 'FAILED' : 'SUCCEEDED' })
  }
  try {
    const response = await client.post(`/admin/courses/${courseId}/recalculate`, {}, { headers: await headers({ 'Idempotency-Key': idempotencyKey('manual', courseId) }) })
    return unwrap(response.data)
  } catch (error) {
    handleError(error)
  }
}

export async function getRecalculationRun(runId) {
  if (useMock) {
    guardMock('run')
    const entry = mockRuns.get(runId)
    if (!entry) throw mockError('RUN_NOT_FOUND', 'run not found', 404)
    entry.polls += 1
    if (entry.polls === 1) entry.run.status = 'RUNNING'
    if (entry.polls >= 2) entry.run.status = entry.terminal
    return clone(entry.run)
  }
  try {
    const response = await client.get(`/admin/recalculation-runs/${runId}`, { headers: await headers() })
    return unwrap(response.data)
  } catch (error) {
    handleError(error)
  }
}

export async function listRuns() {
  if (useMock) {
    guardMock('runs')
    return Array.from(mockRuns.values()).map(entry => clone(entry.run))
  }
  try {
    const response = await client.get('/admin/recalculation-runs', { headers: await headers() })
    return unwrap(response.data) || []
  } catch (error) {
    handleError(error)
  }
}

export async function listApprovals(filters = {}) {
  if (useMock) {
    guardMock('approvals')
    if (mockScenario === 'empty') return []
    return clone(mockApprovals.filter((approval) => (!filters.status || approval.status === filters.status) && (!filters.course_id || approval.course_id.includes(filters.course_id)) && (!filters.student_id || approval.student_id.includes(filters.student_id))))
  }
  try {
    const response = await client.get('/admin/exception-approvals', { params: compactFilters(filters), headers: await headers() })
    return unwrap(response.data) || []
  } catch (error) {
    handleError(error)
  }
}

export async function listCourseOperationApprovals(filters = {}) {
  if (useMock) {
    guardMock('approval')
    return clone(mockCourseOperations.filter((item) => (!filters.status || item.status === filters.status) && (!filters.course_id || item.course_id === filters.course_id)))
  }
  try {
    const response = await client.get('/admin/course-operation-approvals', { params: compactFilters(filters), headers: await headers() })
    return unwrap(response.data) || []
  } catch (error) {
    handleError(error)
  }
}

export async function decideCourseOperation(operationId, decision, comment) {
  if (useMock) {
    guardMock('approval')
    const operation = mockCourseOperations.find((item) => item.id === operationId)
    if (!operation) throw mockError('COURSE_OPERATION_NOT_FOUND', 'course operation not found', 404)
    if (operation.status !== 'PENDING') throw mockError('COURSE_OPERATION_NOT_PENDING', 'course operation is terminal', 409)
    if (!String(comment || '').trim()) throw mockError('EMPTY_COMMENT', 'comment is required', 422)
    if (decision === 'reject') {
      operation.status = 'REJECTED'
      operation.comment = comment
      operation.reviewer_id = 'academic-001'
      addMockAudit({ action: 'COURSE_OPERATION_REJECTED', resourceType: 'course_operation', resourceId: operation.id, courseId: operation.course_id || operation.id, reason: comment, before: { status: 'PENDING' }, after: { status: 'REJECTED' } })
      return { operation: clone(operation), course: operation.course_id ? clone(mockCourses.find((item) => item.id === operation.course_id)) : null, run: null, reused: false }
    }
    let course = null
    let run = null
    if (operation.operation === 'CREATE') {
      course = { id: `course-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`, ...clone(operation.payload), enrolled_count: 0, waitlist_count: 0, status: 'OPEN', version: 1 }
      mockCourses.unshift(course)
      operation.course_id = course.id
      addMockAudit({ action: 'COURSE_CREATED', resourceType: 'course', resourceId: course.id, courseId: course.id, reason: 'course created after approval', after: course })
    } else {
      course = mockCourses.find((item) => item.id === operation.course_id)
      if (!course) throw mockError('COURSE_NOT_FOUND', 'course not found', 404)
      const before = clone(course)
      if (operation.operation === 'UPDATE') {
        const schedulesChanged = JSON.stringify(before.schedules) !== JSON.stringify(operation.payload.schedules)
        const capacityChanged = before.capacity !== operation.payload.capacity
        Object.assign(course, clone(operation.payload), { version: (course.version || 1) + 1, status: 'OPEN' })
        run = capacityChanged || schedulesChanged ? createMockRun(course.id, 'COURSE_UPDATE', { synchronous: true }) : createMockRun(course.id, 'COURSE_UPDATE', { synchronous: true })
        addMockAudit({ action: 'COURSE_UPDATED', resourceType: 'course', resourceId: course.id, courseId: course.id, runId: run.id, reason: 'course details updated after approval', before, after: course })
      } else {
        mockCourses.splice(mockCourses.indexOf(course), 1)
        run = createMockRun(operation.course_id, 'CANCEL', { synchronous: true })
        addMockAudit({ action: 'COURSE_DELETED', resourceType: 'course', resourceId: operation.course_id, courseId: operation.course_id, runId: run.id, reason: operation.payload.reason, before, after: { id: operation.course_id, status: 'DELETED' } })
        course = null
      }
    }
    operation.status = 'APPROVED'
    operation.comment = comment
    operation.reviewer_id = 'academic-001'
    addMockAudit({ action: 'COURSE_OPERATION_APPROVED', resourceType: 'course_operation', resourceId: operation.id, courseId: operation.course_id || operation.id, runId: run?.id, reason: comment, before: { status: 'PENDING' }, after: { status: 'APPROVED' } })
    return { operation: clone(operation), course: course ? clone(course) : null, run: clone(run), reused: false }
  }
  try {
    const action = decision === 'approve' ? 'approve' : 'reject'
    const response = await client.post(`/admin/course-operation-approvals/${operationId}/${action}`, { comment, waived_rules: [] }, { headers: await headers() })
    return unwrap(response.data)
  } catch (error) {
    handleError(error)
  }
}

export async function decideApproval(approvalId, decision, comment, waivedRules = []) {
  if (useMock) {
    guardMock('approval')
    const approval = mockApprovals.find((item) => item.id === approvalId)
    if (!approval) throw mockError('APPROVAL_NOT_FOUND', 'approval not found', 404)
    if (approval.status !== 'PENDING') throw mockError('APPROVAL_NOT_PENDING', 'approval is terminal', 409)
    if (!String(comment || '').trim()) throw mockError('EMPTY_COMMENT', 'comment is required', 422)
    const invalid = waivedRules.filter((rule) => !['CONFLICT', 'TIME_CONFLICT', 'PREREQUISITE_MISSING'].includes(rule))
    if (invalid.length) throw mockError('APPROVAL_RULE_NOT_ALLOWED', 'waived rule is not allowed', 422)
    approval.status = decision === 'approve' ? 'APPROVED' : 'REJECTED'
    approval.comment = comment
    approval.waived_rules = clone(waivedRules)
    addMockAudit({ action: decision === 'approve' ? 'EXCEPTION_APPROVED' : 'EXCEPTION_REJECTED', resourceType: 'exception_approval', resourceId: approvalId, courseId: approval.course_id, reason: comment, subjectStudentId: approval.student_id, before: { status: 'PENDING' }, after: { status: approval.status, waived_rules: waivedRules } })
    return { approval: clone(approval) }
  }
  try {
    const action = decision === 'approve' ? 'approve' : 'reject'
    const response = await client.post(`/admin/exception-approvals/${approvalId}/${action}`, { comment, waived_rules: waivedRules }, { headers: await headers() })
    return unwrap(response.data)
  } catch (error) {
    handleError(error)
  }
}

function filterMockAudits(filters) {
  const from = filters.from ? new Date(filters.from).getTime() : null
  const to = filters.to ? new Date(filters.to).getTime() : null
  return mockAudits.filter((audit) => {
    const courseId = audit.resource_type === 'course' ? audit.resource_id : audit.after_json?.course_id
    const createdAt = new Date(audit.created_at).getTime()
    return (!filters.course_id || courseId?.includes(filters.course_id))
      && (!filters.student_id || audit.subject_student_id?.includes(filters.student_id))
      && (!filters.action || audit.action === filters.action)
      && (!filters.run_id || audit.run_id?.includes(filters.run_id))
      && (!from || createdAt >= from)
      && (!to || createdAt <= to)
  })
}

export async function listAuditsPage(filters = {}) {
  if (useMock) {
    guardMock('audits')
    if (mockScenario === 'empty') return { items: [], meta: { page: 1, page_size: 20, total: 0 } }
    const matched = filterMockAudits(filters)
    const page = Number(filters.page || 1)
    const pageSize = Number(filters.page_size || 20)
    const start = (page - 1) * pageSize
    return { items: clone(matched.slice(start, start + pageSize)), meta: { page, page_size: pageSize, total: matched.length } }
  }
  try {
    const response = await client.get('/admin/audit-logs', { params: normalizeAuditFilters(filters), headers: await headers() })
    return { items: unwrap(response.data) || [], meta: response.data?.meta || { page: 1, page_size: 20, total: 0 } }
  } catch (error) {
    handleError(error)
  }
}

export async function listAudits(filters = {}) {
  return (await listAuditsPage(filters)).items
}

export function isMockMode() {
  return useMock
}
