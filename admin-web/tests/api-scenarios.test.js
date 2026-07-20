import assert from 'node:assert/strict'
import test from 'node:test'

import {
  cancelCourse,
  configureMockScenario,
  createCourse,
  decideCourseOperation,
  expandCourse,
  getRecalculationRun,
  idempotencyKey,
  listCourses,
  startRecalculation,
  updateCourse,
} from '../src/api.js'
import { isTerminalRun, preserveServerResultOrder } from '../src/admin-state.js'

test('normal mock run exposes server order and terminal polling', async () => {
  configureMockScenario('normal')
  const courses = await listCourses({ keyword: 'AI201' })
  assert.equal(courses.length, 1)
  const started = await startRecalculation('course-201')
  assert.equal(started.status, 'PENDING')
  const running = await getRecalculationRun(started.id)
  const done = await getRecalculationRun(started.id)
  assert.equal(running.status, 'RUNNING')
  assert.equal(done.status, 'SUCCEEDED')
  assert.deepEqual(preserveServerResultOrder(done.results).map((item) => item.new_status), ['SKIPPED', 'PROMOTED'])
  assert.equal(isTerminalRun(done.status), true)
})

test('full course expansion promotes the next eligible waitlist candidate', async () => {
  configureMockScenario('normal')
  const [before] = await listCourses({ keyword: 'AI201' })
  assert.equal(before.enrolled_count, before.capacity)
  assert.equal(before.waitlist_count, 2)
  const result = await expandCourse(before.id, 1)
  assert.equal(result.course.capacity, before.capacity + 1)
  assert.equal(result.run.trigger_type, 'EXPAND')
  await getRecalculationRun(result.run.id)
  const done = await getRecalculationRun(result.run.id)
  assert.equal(done.status, 'SUCCEEDED')
  assert.deepEqual(done.results.map((item) => item.new_status), ['SKIPPED', 'PROMOTED'])
  const [after] = await listCourses({ keyword: 'AI201' })
  assert.equal(after.enrolled_count, 2)
  assert.equal(after.waitlist_count, 0)
  await assert.rejects(() => expandCourse(before.id, 0), (error) => error.code === 'INVALID_CAPACITY_DELTA')
})

test('empty, failed, and network-error mock scenarios are explicit', async () => {
  configureMockScenario('empty')
  assert.deepEqual(await listCourses(), [])
  configureMockScenario('failed-run')
  const started = await startRecalculation('course-301')
  await getRecalculationRun(started.id)
  const failed = await getRecalculationRun(started.id)
  assert.equal(failed.status, 'FAILED')
  assert.equal(failed.error.code, 'RECALCULATION_FAILED')
  configureMockScenario('network-error')
  await assert.rejects(() => listCourses(), (error) => error.code === 'NETWORK_ERROR')
  configureMockScenario('normal')
})

test('course operations stay pending until approval and then update state', async () => {
  configureMockScenario('normal')
  const payload = {
    code: 'CS401',
    name: '分布式系统',
    teacher_name: '赵老师',
    credits: 3,
    capacity: 40,
    schedules: [{ weekday: 4, start_minute: 480, end_minute: 570, room: 'D401' }],
    prerequisites: ['CS101'],
  }
  const created = await createCourse(payload)
  assert.equal(created.course, null)
  assert.equal(created.operation.status, 'PENDING')
  const approved = await decideCourseOperation(created.operation.id, 'approve', '批准新增课程')
  assert.equal(approved.course.teacher_name, '赵老师')
  assert.equal(approved.course.capacity, 40)
  const updated = await updateCourse(approved.course.id, { ...payload, capacity: 48, schedules: [{ weekday: 5, start_minute: 600, end_minute: 690, room: 'D402' }] })
  assert.equal(updated.course, null)
  assert.equal(updated.operation.status, 'PENDING')
  const approvedUpdate = await decideCourseOperation(updated.operation.id, 'approve', '批准编辑课程')
  assert.equal(approvedUpdate.course.capacity, 48)
  assert.equal(approvedUpdate.run.trigger_type, 'COURSE_UPDATE')
  await assert.rejects(() => createCourse({ ...payload, code: 'CS101' }), (error) => error.code === 'COURSE_ALREADY_EXISTS')
})

test('deleting a full course closes waitlists and removes it after approval', async () => {
  configureMockScenario('normal')
  const [course] = await listCourses({ keyword: 'AI201' })
  const submitted = await cancelCourse(course.id, '教师停开课程')
  assert.equal(submitted.course, null)
  assert.equal(submitted.operation.status, 'PENDING')
  const approved = await decideCourseOperation(submitted.operation.id, 'approve', '批准删除课程')
  assert.equal(approved.course, null)
  assert.equal(approved.run.trigger_type, 'CANCEL')
  assert.deepEqual(approved.run.results.map((item) => item.new_status), ['CANCELLED_BY_ADMIN', 'CLOSED', 'CLOSED'])
  assert.equal((await listCourses({ keyword: 'AI201' })).length, 0)
})

test('generated idempotency keys stay within the database contract for UUID courses', () => {
  const key = idempotencyKey('cancel', 'cbb7d441-32ba-4972-80d0-548c0fd8b303')
  assert.ok(key.length <= 64)
  assert.match(key, /^cancel-/)
})
