import { describe, expect, it } from 'vitest'
import { mergeSelections } from '../src/utils/selections'

describe('选课记录合并', () => {
  it('只展示有效选课和正在候补记录', () => {
    const records = mergeSelections(
      [{ course_id: 'c1', status: 'ENROLLED' }, { course_id: 'c2', status: 'DROPPED' }],
      [{ course_id: 'c3', status: 'WAITING' }, { course_id: 'c4', status: 'REMOVED' }],
    )
    expect(records.map(item => [item.course_id, item.display_status])).toEqual([['c1', '已选'], ['c3', '候补']])
  })
})
