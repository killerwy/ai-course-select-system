import test from 'node:test'
import assert from 'node:assert/strict'

import {
  ApiError,
  createApiClient,
  createIdempotencyKey,
  unwrapResponse,
} from '../miniprogram/services/http.ts'

function transport(responseOrError) {
  const calls = []
  return {
    calls,
    async request(options) {
      calls.push(options)
      if (responseOrError instanceof Error) throw responseOrError
      return responseOrError
    },
  }
}

test('MP-03 normal: unwraps envelope and injects authorization without exposing it in result', async () => {
  const mock = transport({
    statusCode: 200,
    data: { data: [{ id: 'course-1' }], meta: { request_id: 'req-server' } },
  })
  const client = createApiClient({
    transport: mock,
    getAccessToken: () => 'test-token-value',
  })
  const result = await client.request('/courses')
  assert.equal(result.compat, 'envelope')
  assert.equal(result.meta.request_id, 'req-server')
  assert.equal(mock.calls[0].headers.Authorization, 'Bearer test-token-value')
  assert.equal(JSON.stringify(result).includes('test-token-value'), false)
})

test('MP-03 compatibility: supports naked array and legacy naked login object', () => {
  assert.equal(unwrapResponse([], 'req-array').compat, 'naked-array')
  const login = unwrapResponse({ access_token: 'redacted', token_type: 'bearer', user: { role: 'STUDENT' } }, 'req-login')
  assert.equal(login.compat, 'naked-object')
  assert.equal(login.meta.request_id, 'req-login')
})

test('MP-03 write: preserves caller idempotency key and keeps it within 64 characters', async () => {
  const mock = transport({ statusCode: 200, data: { data: { status: 'ENROLLED' }, meta: { request_id: 'req-write' } } })
  const client = createApiClient({ transport: mock })
  const key = createIdempotencyKey('enroll', 'same-retry')
  await client.request('/students/me/enrollment-requests', { method: 'POST', data: {}, idempotencyKey: key })
  await client.request('/students/me/enrollment-requests', { method: 'POST', data: {}, idempotencyKey: key })
  assert.equal(mock.calls[0].headers['Idempotency-Key'], key)
  assert.equal(mock.calls[1].headers['Idempotency-Key'], key)
  assert.ok(key.length <= 64)
})

test('MP-03 auth/error: maps 401 and invokes unauthorized exactly once', async () => {
  let unauthorized = 0
  const mock = transport({
    statusCode: 401,
    data: {
      error: { code: 'UNAUTHORIZED', message: 'expired', details: [] },
      meta: { request_id: 'req-401' },
    },
  })
  const client = createApiClient({ transport: mock, onUnauthorized: () => { unauthorized += 1 } })
  await assert.rejects(() => client.request('/me'), error => {
    assert.ok(error instanceof ApiError)
    assert.equal(error.code, 'UNAUTHORIZED')
    assert.equal(error.statusCode, 401)
    return true
  })
  assert.equal(unauthorized, 1)
})

test('MP-03 error: preserves 409/422 details and marks 5xx retryable', async () => {
  for (const pair of [[409, 'CAPACITY_FULL'], [422, 'VALIDATION_ERROR'], [500, 'INTERNAL_ERROR']]) {
    const statusCode = pair[0]
    const code = pair[1]
    const client = createApiClient({
      transport: transport({
        statusCode,
        data: { error: { code, message: code, details: [{ field: 'fixture' }] }, meta: { request_id: 'req-' + statusCode } },
      }),
    })
    await assert.rejects(() => client.request('/fixture'), error => {
      assert.equal(error.code, code)
      assert.equal(error.details[0].field, 'fixture')
      assert.equal(error.retryable, statusCode >= 500)
      return true
    })
  }
})

test('MP-03 network: distinguishes timeout from network error', async () => {
  const timeoutClient = createApiClient({ transport: transport(new Error('request:fail timeout')) })
  await assert.rejects(() => timeoutClient.request('/courses'), error => error.code === 'REQUEST_TIMEOUT')
  const networkClient = createApiClient({ transport: transport(new Error('request:fail network')) })
  await assert.rejects(() => networkClient.request('/courses'), error => error.code === 'NETWORK_ERROR')
})

test('MP-03 boundary: invalid idempotency key is rejected before transport', async () => {
  const mock = transport({ statusCode: 200, data: {} })
  const client = createApiClient({ transport: mock })
  await assert.rejects(
    () => client.request('/write', { method: 'POST', idempotencyKey: 'x'.repeat(65) }),
    error => error.code === 'INVALID_IDEMPOTENCY_KEY',
  )
  assert.equal(mock.calls.length, 0)
})

