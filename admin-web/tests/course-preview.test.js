import assert from 'node:assert/strict'
import test from 'node:test'

import { configureMockScenario, listCourses, previewCourseChange } from '../src/api.js'

test('course change preview is read-only and includes the proposed time-conflict count', async () => {
  configureMockScenario('normal')
  const [course] = await listCourses({ keyword: 'AI201' })
  const preview = await previewCourseChange(course.id, {
    operation: 'UPDATE',
    capacity: course.capacity + 2,
    schedules: [{ weekday: 2, start_minute: 600, end_minute: 690, room: 'B202' }],
  })
  assert.equal(preview.course_code, 'AI201')
  assert.equal(preview.promoted, 2)
  assert.equal(preview.waiting, 0)
  assert.equal(preview.conflicts, 1)
  const [unchanged] = await listCourses({ keyword: 'AI201' })
  assert.equal(unchanged.capacity, course.capacity)
})
