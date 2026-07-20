import test from 'node:test'
import assert from 'node:assert/strict'
import { parseAcademicHandoff } from '../src/session-handoff.js'

test('解析统一登录页发送的教师会话', () => {
  assert.deepEqual(parseAcademicHandoff('#access_token=jwt.demo.token&role=ACADEMIC'), {
    accessToken: 'jwt.demo.token',
    role: 'ACADEMIC',
  })
})

test('拒绝空 token 和非教师角色', () => {
  assert.equal(parseAcademicHandoff('#access_token=&role=ACADEMIC'), null)
  assert.equal(parseAcademicHandoff('#access_token=student-token&role=STUDENT'), null)
  assert.equal(parseAcademicHandoff(''), null)
})
