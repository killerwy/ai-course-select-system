import { describe, expect, it } from 'vitest'
import { normalizeLiveInterval } from '../src/composables/useLiveQuery'

describe('实时查询', () => {
  it('课程同步间隔有最小边界和默认值', () => {
    expect(normalizeLiveInterval(500)).toBe(1000)
    expect(normalizeLiveInterval(Number.NaN)).toBe(5000)
    expect(normalizeLiveInterval(8000)).toBe(8000)
  })
})
