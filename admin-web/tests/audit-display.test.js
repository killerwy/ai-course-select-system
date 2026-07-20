import assert from 'node:assert/strict'
import test from 'node:test'

import {
  auditActionLabel,
  auditChangeDescription,
  auditDescription,
  courseImpactDialogOptions,
  courseImpactMessage,
  describeCourseOperation,
  describeRunResult,
} from '../src/admin-state.js'

test('teacher audit records and operation details are rendered as Chinese descriptions', () => {
  const audit = {
    action: 'COURSE_EXPANDED',
    resource_type: 'course',
    resource_id: 'course-201',
    before_json: { code: 'AI201', name: '人工智能导论', capacity: 30 },
    after_json: { code: 'AI201', name: '人工智能导论', capacity: 35 },
    reason: 'capacity +5',
  }
  assert.equal(auditActionLabel(audit.action), '课程扩容')
  assert.equal(auditDescription(audit), '已为课程《AI201 人工智能导论》扩容。')
  assert.match(auditChangeDescription(audit), /课程容量：30 人 → 35 人/)
  assert.doesNotMatch(auditChangeDescription(audit), /\{|\}/)
  assert.match(describeCourseOperation({ operation: 'CANCEL', payload: { reason: '教师停开课程' } }), /删除原因：教师停开课程/)
  assert.match(describeRunResult({ reason_code: 'COURSE_CANCELLED', details: {} }), /课程已删除/)
  assert.equal(
    courseImpactMessage({ course_code: 'AI201', course_name: '人工智能导论', enrolled_count: 3, promoted: 2, waiting: 1, conflicts: 4, errors: 0 }),
    '本次变更 AI201 人工智能导论 · 课程已选人数 3 人 · 候补通过 2 人 · 仍在候补 1 人 · 修改时间后与学生已选课程时间冲突 4 人 · 错误操作 0。',
  )
  assert.equal(courseImpactDialogOptions().center, true)
  assert.equal(courseImpactDialogOptions().confirmButtonText, '确认')
  assert.equal(courseImpactDialogOptions().cancelButtonText, '取消')
})
