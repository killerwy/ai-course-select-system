import assert from 'node:assert/strict'
import test from 'node:test'

import {
  configureMockScenario,
  decideApproval,
  listApprovals,
  listAuditsPage,
} from '../src/api.js'

test('mock approval and audit filters preserve safe state', async () => {
  configureMockScenario('normal')
  const pending = await listApprovals({ status: 'PENDING' })
  assert.equal(pending.length, 1)
  await decideApproval(pending[0].id, 'approve', '确认时间冲突豁免', ['TIME_CONFLICT'])
  const approvals = await listApprovals({ status: 'APPROVED' })
  assert.equal(approvals.length, 1)
  const audits = await listAuditsPage({ course_id: 'course-201', page: 1, page_size: 10 })
  assert.ok(audits.meta.total >= 1)
  assert.ok(audits.items.some((item) => item.action === 'EXCEPTION_APPROVED'))
})
