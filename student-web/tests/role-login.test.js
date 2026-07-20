import { describe, expect, it } from 'vitest'
import { assertSelectedRole, buildAcademicHandoffUrl } from '../src/auth/role-login'

describe('角色登录', () => {
  it('角色切换只允许账号进入对应端', () => {
    expect(() => assertSelectedRole({ role: 'STUDENT' }, 'STUDENT')).not.toThrow()
    try {
      assertSelectedRole({ role: 'STUDENT' }, 'ACADEMIC')
      throw new Error('expected role mismatch')
    } catch (error) {
      expect(error.code).toBe('ROLE_MISMATCH')
    }
  })

  it('教师会话使用 fragment 交接且不进入查询参数', () => {
    const target = new URL(buildAcademicHandoffUrl('http://127.0.0.1:5174', 'jwt.demo.token'))
    expect(target.search).toBe('')
    expect(target.hash).toContain('access_token=jwt.demo.token')
    expect(target.hash).toContain('role=ACADEMIC')
  })
})
