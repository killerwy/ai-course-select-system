import test from 'node:test'
import assert from 'node:assert/strict'
import { createWechatAuthService } from '../miniprogram/services/wechat-auth.ts'
import { createReadonlyCache } from '../miniprogram/utils/cache.ts'
import { redactSensitive } from '../miniprogram/utils/redact.ts'

test('MP-17 boundary: WeChat adapter sends code only and rejects short values', async () => {
  const calls = []
  const service = createWechatAuthService({
    async request(path, options) {
      calls.push({ path, options })
      return { data: { access_token: 'token', token_type: 'bearer', user: { id: 'student-1', username: 's', role: 'STUDENT' } }, meta: { request_id: 'r' }, compat: 'envelope' }
    },
  })
  await assert.rejects(() => service.login('x'), error => error.code === 'INVALID_WECHAT_CODE')
  await service.login('valid-code')
  assert.equal(calls[0].path, '/auth/wechat-login')
  assert.deepEqual(calls[0].options.data, { code: 'valid-code' })
  assert.equal('appSecret' in calls[0].options.data, false)
})

test('MP-18 security: recursive redaction never exposes credential-like keys', () => {
  const safe = redactSensitive({ access_token: 'a', nested: [{ password: 'p', name: 'ok' }], appSecret: 's' })
  assert.deepEqual(safe, { access_token: '[REDACTED]', nested: [{ password: '[REDACTED]', name: 'ok' }], appSecret: '[REDACTED]' })
})

test('MP-18 cache: stale snapshots are readable but explicitly marked stale', () => {
  let value
  const storage = { get: () => value, set: (_key, next) => { value = next }, remove: () => { value = undefined } }
  const cache = createReadonlyCache(storage, 'courses', 0)
  cache.write([{ id: 'course-1' }])
  const entry = cache.read()
  assert.equal(entry.stale, true)
  assert.deepEqual(entry.value, [{ id: 'course-1' }])
})
