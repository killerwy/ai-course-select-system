import test from 'node:test'
import assert from 'node:assert/strict'

import { createStudentService, filterCourseList, hasExpectedRecommendationRequest } from '../miniprogram/services/student.ts'

const course = (overrides = {}) => ({
  id: 'course-1',
  code: 'CS101',
  name: '软件工程实践',
  teacher_name: '李老师',
  credits: 3,
  capacity: 2,
  enrolled_count: 1,
  waitlist_count: 0,
  status: 'OPEN',
  schedules: [{ weekday: 1, start_minute: 540, end_minute: 630, room: 'A' }],
  prerequisites: [],
  ...overrides,
})

function client(response) {
  const calls = []
  return {
    calls,
    async request(path, options) {
      calls.push({ path, options })
      return { data: response, meta: { request_id: 'req-student' }, compat: 'envelope' }
    },
  }
}

test('MP-06 normal: filters code/name/teacher without changing course state', () => {
  const courses = [course(), course({ id: 'course-2', code: 'AI202', name: '人工智能', teacher_name: '王老师', schedules: [{ weekday: 3, start_minute: 600, end_minute: 690, room: 'B' }] })]
  assert.equal(filterCourseList(courses, { keyword: 'ai' })[0].id, 'course-2')
  assert.equal(filterCourseList(courses, { keyword: '王老师' })[0].id, 'course-2')
  assert.equal(filterCourseList(courses, { weekday: 1 })[0].id, 'course-1')
  assert.equal(filterCourseList(courses, { period: 3 })[0].id, 'course-2')
  assert.equal(filterCourseList(courses, { status: 'OPEN' }).length, 2)
})

test('MP-06 boundary: empty and unknown filters return safe results', () => {
  const courses = [course()]
  assert.deepEqual(filterCourseList(courses, { keyword: 'missing' }), [])
  assert.deepEqual(filterCourseList(courses, { weekday: 7 }), [])
  assert.deepEqual(filterCourseList(courses, { status: 'SERVER_NEW_STATUS' }), [])
})

test('MP-08/09 contract: recommendation and enrollment requests whitelist fields', async () => {
  const mock = client({ id: 'session-1', status: 'FALLBACK', items: [] })
  const service = createStudentService(mock)
  await service.createRecommendations({ goals: 'AI', preferences: ['实践'] })
  assert.deepEqual(mock.calls[0].options.data, { goals: 'AI', preferences: ['实践'] })
  assert.equal(hasExpectedRecommendationRequest(mock.calls[0].options.data), true)
  await service.requestEnrollment('course-1', 'WAITLIST', 'same-key')
  assert.deepEqual(mock.calls[1].options.data, { course_id: 'course-1', type: 'WAITLIST' })
  assert.equal(mock.calls[1].options.idempotencyKey, 'same-key')
})

test('MP-06/07 error boundary: malformed course arrays are empty and IDs are encoded', async () => {
  const mock = client([{ id: 'not-a-course' }])
  const service = createStudentService(mock)
  const result = await service.listCourses({ keyword: 'x' })
  assert.deepEqual(result.data, [])
  await service.getCourse('course/with space')
  assert.equal(mock.calls[1].path, '/courses/course%2Fwith%20space')
})

test('MP-10 compatibility: normalizes object and legacy array schedule responses', async () => {
  const objectMock = client({ courses: [{ course_id: 'c1', status: 'ENROLLED', weekday: 1, start_minute: 1, end_minute: 2, room: 'A' }], generated_at: 'fixture' })
  const objectResult = await createStudentService(objectMock).getSchedule()
  assert.equal(objectResult.data.courses.length, 1)
  assert.equal(objectResult.data.generated_at, 'fixture')
  const arrayMock = client([{ course_id: 'c2', status: 'ENROLLED', weekday: 2, start_minute: 1, end_minute: 2, room: 'B' }])
  const arrayResult = await createStudentService(arrayMock).getSchedule()
  assert.equal(arrayResult.data.courses[0].course_id, 'c2')
})

test('MP-27 schedule: expands selected course summaries into timetable lessons', async () => {
  const nestedMock = client({ courses: [course()], generated_at: 'database-fixture', cache_backend: 'database' })
  const result = await createStudentService(nestedMock).getSchedule()
  assert.deepEqual(result.data.courses, [{
    course_id: 'course-1',
    course_code: 'CS101',
    course_name: '软件工程实践',
    teacher_name: '李老师',
    status: 'ENROLLED',
    weekday: 1,
    start_minute: 540,
    end_minute: 630,
    room: 'A',
  }])
  assert.equal(result.data.generated_at, 'database-fixture')
  assert.equal(result.data.cache_backend, 'database')
})
