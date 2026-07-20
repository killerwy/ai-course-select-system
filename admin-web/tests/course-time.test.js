import assert from 'node:assert/strict'
import test from 'node:test'

import { COURSE_PERIODS, formatScheduleText, minutesToPeriod, periodToMinutes } from '../src/admin-state.js'

test('academic schedule uses ten one-hour periods with midday and evening gaps', () => {
  assert.equal(COURSE_PERIODS.length, 10)
  assert.equal(periodToMinutes(1), 480)
  assert.equal(periodToMinutes(5), 840)
  assert.equal(periodToMinutes(9), 1140)
  assert.equal(periodToMinutes(10) + 60, 1260)
  assert.equal(minutesToPeriod(1200), 10)
  assert.match(formatScheduleText({ weekday: 7, start_minute: 1200, end_minute: 1260, room: 'E201' }), /周日 第10节 20:00-21:00/)
})
