import test from 'node:test'
import assert from 'node:assert/strict'

import { enrolledSchedule, enrollmentSummary, ownAuditLogs } from '../miniprogram/domain/student-state.ts'

test('MP-10 normal: summarizes enrolled, conflict, waiting and terminal states', () => {
  const summary = enrollmentSummary(
    [
      { id: 'e1', student_id: 's1', course_id: 'c1', status: 'ENROLLED' },
      { id: 'e2', student_id: 's1', course_id: 'c2', status: 'CONFLICT_REVIEW' },
      { id: 'e3', student_id: 's1', course_id: 'c3', status: 'DROPPED' },
    ],
    [{ id: 'w1', student_id: 's1', course_id: 'c4', status: 'WAITING' }],
  )
  assert.deepEqual(summary, { enrolled: 1, conflictReview: 1, waiting: 1, terminal: 1 })
})

test('MP-10 boundary: waitlist never occupies schedule and audit is scoped', () => {
  assert.deepEqual(enrolledSchedule([
    { course_id: 'c1', status: 'ENROLLED', weekday: 1, start_minute: 1, end_minute: 2, room: 'A' },
    { course_id: 'c2', status: 'CONFLICT_REVIEW', weekday: 2, start_minute: 1, end_minute: 2, room: 'B' },
    { course_id: 'c3', status: 'WAITING', weekday: 3, start_minute: 1, end_minute: 2, room: 'C' },
  ]).map(item => item.course_id), ['c1', 'c2'])
  assert.deepEqual(ownAuditLogs([
    { id: 'a1', actor_id: 's1', actor_role: 'STUDENT', action: 'x', resource_type: 'x', resource_id: 'x', before_json: {}, after_json: {}, request_id: 'r1', created_at: 'x' },
    { id: 'a2', actor_id: 's2', actor_role: 'STUDENT', action: 'x', resource_type: 'x', resource_id: 'x', before_json: {}, after_json: {}, request_id: 'r2', created_at: 'x' },
  ], 's1').map(item => item.id), ['a1'])
})
