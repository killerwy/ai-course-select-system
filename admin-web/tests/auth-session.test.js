import assert from 'node:assert/strict'
import test from 'node:test'

import {
  hasAcademicSession,
  isAuthenticationError,
  loginAcademic,
  logoutAcademic,
  restoreAcademicSession,
} from '../src/api.js'

test('real-mode session helpers keep login, restore, logout, and 401 detection explicit', async () => {
  logoutAcademic()
  assert.equal(hasAcademicSession(), false)
  assert.equal(isAuthenticationError({ response: { status: 401 } }), true)
  await assert.rejects(() => loginAcademic('', ''), (error) => {
    assert.equal(error.code, 'UNAUTHORIZED')
    return true
  })

  const result = await loginAcademic('academic', 'academic123')
  assert.equal(result.user.role, 'ACADEMIC')
  assert.equal(hasAcademicSession(), true)
  const restored = await restoreAcademicSession()
  assert.equal(restored.role, 'ACADEMIC')

  logoutAcademic()
  assert.equal(hasAcademicSession(), false)
})
