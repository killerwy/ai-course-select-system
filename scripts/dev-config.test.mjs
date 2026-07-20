import test from 'node:test'
import assert from 'node:assert/strict'
import { createDevApps } from './dev-config.mjs'

test('统一启动配置生成两个不同端口的前端', () => {
  const [student, admin] = createDevApps({ DEV_HOST: '127.0.0.1', STUDENT_WEB_PORT: '6201', ADMIN_WEB_PORT: '6202' })
  assert.equal(student.url, 'http://127.0.0.1:6201')
  assert.equal(student.env.VITE_ADMIN_WEB_URL, admin.url)
  assert.equal(admin.env.VITE_PORTAL_URL, `${student.url}/login`)
  assert.equal(student.env.VITE_USE_MOCK, 'false')
  assert.equal(admin.env.VITE_USE_MOCK, 'false')
})

test('拒绝学生端和教师端使用相同或非法端口', () => {
  assert.throws(() => createDevApps({ STUDENT_WEB_PORT: '5173', ADMIN_WEB_PORT: '5173' }), /INVALID_WEB_PORTS/)
  assert.throws(() => createDevApps({ STUDENT_WEB_PORT: '0', ADMIN_WEB_PORT: '5174' }), /INVALID_WEB_PORTS/)
})
