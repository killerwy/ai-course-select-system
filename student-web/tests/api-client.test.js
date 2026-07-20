import { describe, expect, it } from 'vitest'
import { errorMessage, unwrapResponse } from '../src/api/client'

describe('API client', () => {
  it('同时解析 MySQL 信封与 memory 裸响应', () => {
    expect(unwrapResponse({ data: { data: [{ id: 'c1' }], meta: { request_id: 'courses' } } })).toEqual([{ id: 'c1' }])
    expect(unwrapResponse({ data: [{ id: 'c2' }] })).toEqual([{ id: 'c2' }])
  })

  it('把选课失败原因转换成中文说明', () => {
    expect(errorMessage({ apiError: { message: 'DUPLICATE' } })).toContain('已选过')
    expect(errorMessage({ apiError: { message: 'CONFLICT' } })).toContain('时间冲突')
    expect(errorMessage({ response: { data: { detail: { decision: 'PREREQUISITE_MISSING' } } }, apiError: { message: 'PREREQUISITE_MISSING' } })).toContain('前置课程')
    expect(errorMessage({ apiError: { message: '网络请求失败' } })).toBe('网络请求失败')
    expect(errorMessage({ response: { data: { detail: [{ loc: ['body', 'password'], type: 'string_too_short', ctx: { min_length: 6 } }] } } })).toContain('密码至少需要 6')
  })
})
