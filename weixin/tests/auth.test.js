import test from 'node:test'
import assert from 'node:assert/strict'

import { ApiError } from '../miniprogram/services/http.ts'
import {
  SESSION_STORAGE_KEY,
  createAuthService,
  createSessionStore,
} from '../miniprogram/services/auth.ts'

function memoryStorage(initial) {
  const values = new Map(Object.entries(initial ?? {}))
  return {
    values,
    get: key => values.get(key),
    set: (key, value) => values.set(key, value),
    remove: key => values.delete(key),
  }
}

function mockClient(steps) {
  const calls = []
  return {
    calls,
    async request(path, options) {
      calls.push({ path, options })
      const step = steps.shift()
      if (step instanceof Error) throw step
      return { data: step, meta: { request_id: 'req-auth' }, compat: 'envelope' }
    },
  }
}

const studentLogin = {
  access_token: 'token-fixture-student',
  token_type: 'bearer',
  user: { id: 'student-fixture-001', username: 'student-fixture', role: 'STUDENT' },
}

test('MP-04 normal: login stores minimal session and never stores password', async () => {
  const storage = memoryStorage()
  const store = createSessionStore(storage, () => 1000)
  const client = mockClient([studentLogin])
  const auth = createAuthService(client, store)
  const session = await auth.login({ username: 'student-fixture', password: 'not-persisted' }, 'STUDENT')
  assert.equal(session.user.role, 'STUDENT')
  const persisted = storage.values.get(SESSION_STORAGE_KEY)
  assert.deepEqual(Object.keys(persisted).sort(), ['accessToken', 'expiresAt', 'user'])
  assert.equal(JSON.stringify(persisted).includes('not-persisted'), false)
  assert.equal(JSON.stringify(persisted).includes('session_key'), false)
})

test('MP-04 cold start: /me is authoritative and refreshes user summary', async () => {
  const storage = memoryStorage({
    [SESSION_STORAGE_KEY]: {
      accessToken: 'token-fixture',
      user: { id: 'student-fixture-001', username: 'old-name', role: 'STUDENT' },
      expiresAt: 9000,
    },
  })
  const store = createSessionStore(storage, () => 1000)
  const client = mockClient([{ id: 'student-fixture-001', username: 'server-name', role: 'STUDENT' }])
  const auth = createAuthService(client, store)
  const session = await auth.restore('STUDENT')
  assert.equal(session.user.username, 'server-name')
  assert.equal(client.calls[0].path, '/me')
})

test('MP-04 boundary: expired or malformed storage is removed without request', async () => {
  for (const cached of [
    { accessToken: 'x', user: { role: 'STUDENT' }, expiresAt: 9000 },
    { accessToken: 'x', user: { id: '1', username: 'u', role: 'STUDENT' }, expiresAt: 999 },
  ]) {
    const storage = memoryStorage({ [SESSION_STORAGE_KEY]: cached })
    const store = createSessionStore(storage, () => 1000)
    const client = mockClient([])
    const auth = createAuthService(client, store)
    assert.equal(await auth.restore(), undefined)
    assert.equal(storage.values.has(SESSION_STORAGE_KEY), false)
    assert.equal(client.calls.length, 0)
  }
})

test('MP-04 error: role mismatch and 401 clear session', async () => {
  const storage = memoryStorage()
  const store = createSessionStore(storage, () => 1000)
  const wrongRoleClient = mockClient([{
    access_token: 'token-academic',
    token_type: 'bearer',
    user: { id: 'academic-fixture', username: 'academic', role: 'ACADEMIC' },
  }])
  const auth = createAuthService(wrongRoleClient, store)
  await assert.rejects(
    () => auth.login({ username: 'academic', password: 'not-persisted' }, 'STUDENT'),
    error => error.code === 'ROLE_MISMATCH',
  )
  assert.equal(storage.values.has(SESSION_STORAGE_KEY), false)

  store.save(studentLogin)
  const unauthorized = new ApiError({ code: 'UNAUTHORIZED', message: 'expired', statusCode: 401 })
  const restoreAuth = createAuthService(mockClient([unauthorized]), store)
  await assert.rejects(() => restoreAuth.restore(), error => error.code === 'UNAUTHORIZED')
  assert.equal(storage.values.has(SESSION_STORAGE_KEY), false)
})

test('MP-04 logout and role guard reject missing or incorrect session', async () => {
  const storage = memoryStorage()
  const store = createSessionStore(storage, () => 1000)
  const auth = createAuthService(mockClient([]), store)
  assert.throws(() => auth.requireRole('STUDENT'), error => error.code === 'UNAUTHORIZED')
  store.save(studentLogin)
  assert.equal(auth.requireRole('STUDENT').id, 'student-fixture-001')
  assert.throws(() => auth.requireRole('ACADEMIC'), error => error.code === 'ROLE_MISMATCH')
  auth.logout()
  assert.equal(storage.values.has(SESSION_STORAGE_KEY), false)
})

