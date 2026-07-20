import test from 'node:test'
import assert from 'node:assert/strict'
import { createAcademicService, pollRun } from '../miniprogram/services/academic.ts'
import { canDecide, runProgress, validateCourseWrite } from '../miniprogram/domain/academic-view.ts'

function result(data) {
  return { data, meta: { request_id: 'test-request' }, compat: 'envelope' }
}

test('MP-13 service: admin paths, query filters and write payloads are explicit', async () => {
  const calls = []
  const service = createAcademicService({
    async request(path, options = {}) {
      calls.push({ path, options })
      if (path.startsWith('/admin/courses?')) return result([])
      return result({ run: { id: 'run-1', status: 'PENDING' } })
    },
  })
  await service.listCourses({ keyword: 'CS', status: 'OPEN', page: 2, pageSize: 10 })
  await service.createCourse({ code: 'CS1', name: '算法', teacher_name: '老师', credits: 3, capacity: 20, schedules: [], prerequisites: [] }, 'create-key')
  assert.equal(calls[0].path, '/admin/courses?keyword=CS&status=OPEN&page=2&page_size=10')
  assert.equal(calls[1].options.idempotencyKey, 'create-key')
  assert.deepEqual(calls[1].options.data.prerequisites, [])
})

test('MP-15 polling: stops at terminal state and respects bounded attempts', async () => {
  const statuses = ['PENDING', 'RUNNING', 'SUCCEEDED']
  let index = 0
  const delays = []
  const final = await pollRun(async () => result({ id: 'run-1', status: statuses[Math.min(index++, statuses.length - 1)] }), 'run-1', {
    attempts: 5,
    intervalMs: 10,
    sleep: async ms => delays.push(ms),
  })
  assert.equal(final.data.status, 'SUCCEEDED')
  assert.deepEqual(delays, [10, 10])
})

test('MP-13 boundary: course validation and approval state are fail-closed', () => {
  assert.ok(validateCourseWrite({ code: '', name: '', teacher_name: '', credits: 0, capacity: 0, schedules: [] }).length >= 5)
  assert.equal(canDecide('APPROVED'), false)
  assert.equal(canDecide('PENDING'), true)
  assert.equal(runProgress('UNKNOWN'), '未知状态')
})
