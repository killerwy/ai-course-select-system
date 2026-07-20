import { describe, expect, it } from 'vitest'
import { prerequisiteCourseNames } from '../src/utils/course-display'

describe('课程展示', () => {
  it('先修课程内部 ID 或编号显示为具体课程名称', () => {
    const catalog = [{ id: 'course-101', code: 'CS101', name: '程序设计基础' }]
    expect(prerequisiteCourseNames(['course-101'], catalog)).toEqual(['程序设计基础'])
    expect(prerequisiteCourseNames(['CS101'], catalog)).toEqual(['程序设计基础'])
    expect(prerequisiteCourseNames(['missing-course'], catalog)).toEqual(['missing-course'])
  })
})
