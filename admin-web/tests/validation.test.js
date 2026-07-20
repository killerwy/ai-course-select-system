import assert from 'node:assert/strict'
import test from 'node:test'

import {
  allowedWaivedRules,
  isCourseCodeConflict,
  isCourseEditorError,
  prettyJson,
  redactAuditSnapshot,
  userMessageForError,
  validateRequiredText,
  validateSchedule,
} from '../src/admin-state.js'

test('frontend validation, whitelist, and redaction are deterministic', () => {
  assert.equal(validateSchedule({ weekday: 2, start_minute: 600, end_minute: 690 }), '')
  assert.match(validateSchedule({ weekday: 2, start_minute: 700, end_minute: 690 }), /早于/)
  assert.match(validateRequiredText(' ', '审批意见'), /审批意见/)
  assert.deepEqual(allowedWaivedRules(['CONFLICT', 'DUPLICATE', 'TIME_CONFLICT']), ['CONFLICT', 'TIME_CONFLICT'])
  const safe = redactAuditSnapshot({ authorization: 'Bearer demo', nested: { api_key: 'secret', status: 'SKIPPED' } })
  assert.equal(safe.authorization, '[REDACTED]')
  assert.equal(safe.nested.api_key, '[REDACTED]')
  assert.equal(safe.nested.status, 'SKIPPED')
  assert.match(prettyJson(safe), /REDACTED/)
  assert.equal(userMessageForError({ code: 'CONCURRENT_MODIFICATION' }), '课程已被其他操作更新，请刷新后重试')
  assert.equal(userMessageForError({ code: 'PREREQUISITE_NOT_FOUND' }), '先修课程编号不存在，请检查后再提交')
  assert.equal(isCourseCodeConflict({ code: 'COURSE_ALREADY_EXISTS' }), true)
  assert.equal(isCourseCodeConflict({ code: 'CONCURRENT_MODIFICATION' }), false)
  assert.equal(isCourseEditorError({ code: 'PREREQUISITE_NOT_FOUND' }), true)
  assert.equal(isCourseEditorError({ code: 'CONCURRENT_MODIFICATION' }), false)
})
