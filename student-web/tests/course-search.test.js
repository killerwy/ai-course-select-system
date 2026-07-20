import { describe, expect, it } from 'vitest'
import { matchesCourse } from '../src/utils/course-search'

describe('课程搜索', () => {
  it('覆盖代码、名称与教师', () => {
    const course = { code: 'AI201', name: '人工智能导论', teacher_name: '李老师' }
    expect(matchesCourse(course, 'ai201')).toBe(true)
    expect(matchesCourse(course, '李老师')).toBe(true)
    expect(matchesCourse(course, '数据库')).toBe(false)
  })
})
