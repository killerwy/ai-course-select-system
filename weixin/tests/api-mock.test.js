import test from 'node:test'
import assert from 'node:assert/strict'
import { ApiError } from '../miniprogram/services/http.ts'
import { errorMessage, isErrorEnvelope } from '../miniprogram/domain/guards.ts'

test('MP-19 API mock: common HTTP errors remain typed and user-safe', () => {
  const cases = [
    ['CONFLICT', '冲突'],
    ['PREREQUISITE_MISSING', '先修'],
    ['UNAUTHORIZED', '请重新登录'],
    ['FORBIDDEN', '无权'],
    ['CAPACITY_FULL', '已满'],
    ['VALIDATION_ERROR', '不符合'],
  ]
  for (const [code, fragment] of cases) {
    const error = new ApiError({ code, statusCode: code === 'UNAUTHORIZED' ? 401 : 409, message: errorMessage(code), details: [{ reason: 'mock' }] })
    assert.equal(error.code, code)
    assert.match(error.message, new RegExp(fragment))
    assert.deepEqual(error.details, [{ reason: 'mock' }])
  }
})

test('MP-19 API mock: malformed error payloads are rejected before rendering', () => {
  assert.equal(isErrorEnvelope({ error: { code: 'FORBIDDEN', message: 'x', details: [] }, meta: { request_id: 'r' } }), true)
  assert.equal(isErrorEnvelope({ error: { code: 'FORBIDDEN', message: 'x' }, meta: { request_id: 'r' } }), false)
})
