import test from 'node:test'
import assert from 'node:assert/strict'

import {
  errorMessage,
  isCourseSchedule,
  isCourseSummary,
  isErrorEnvelope,
  isSuccessEnvelope,
  isTerminalRunStatus,
  safeCourseList,
  statusLabel,
} from '../miniprogram/domain/guards.ts'

const course = {
  id: 'course-fixture-open',
  code: 'CS-F101',
  name: '软件工程实践',
  teacher_name: '李老师',
  credits: 3,
  capacity: 2,
  enrolled_count: 1,
  waitlist_count: 1,
  status: 'OPEN',
  schedules: [{ weekday: 1, start_minute: 540, end_minute: 630, room: 'A-101' }],
  prerequisites: [],
}

test('MP-02 normal: accepts frozen course and success envelope', () => {
  assert.equal(isCourseSummary(course), true)
  assert.equal(isSuccessEnvelope({ data: [course], meta: { request_id: 'req-fixture' } }), true)
  assert.equal(statusLabel('ENROLLED'), '已选')
})

test('MP-02 boundary: unknown statuses remain unknown and never terminal', () => {
  assert.equal(statusLabel('SERVER_NEW_STATUS'), '未知')
  assert.equal(isTerminalRunStatus('SERVER_NEW_STATUS'), false)
  assert.equal(isTerminalRunStatus('SUCCEEDED'), true)
  assert.equal(isTerminalRunStatus('FAILED'), true)
})

test('MP-02 boundary: rejects invalid schedule and filters malformed courses', () => {
  assert.equal(isCourseSchedule({ weekday: 0, start_minute: 600, end_minute: 600, room: 'A' }), false)
  assert.deepEqual(safeCourseList([course, { ...course, status: 'LOCAL_SUCCESS' }, null]), [course])
})

test('MP-02 error: accepts standard error envelope and maps unknown code safely', () => {
  assert.equal(isErrorEnvelope({
    error: { code: 'FORBIDDEN', message: 'forbidden', details: [] },
    meta: { request_id: 'req-error' },
  }), true)
  assert.equal(errorMessage('FORBIDDEN'), '当前账号无权执行此操作')
  assert.equal(errorMessage('SERVER_NEW_ERROR'), '请求失败，请稍后重试')
})

test('MP-02 error: incomplete envelopes and negative course values are rejected', () => {
  assert.equal(isSuccessEnvelope({ data: [], meta: {} }), false)
  assert.equal(isErrorEnvelope({ error: { code: 'X', message: '', details: [] }, meta: { request_id: 'r' } }), false)
  assert.equal(isCourseSummary({ ...course, capacity: -1 }), false)
})

