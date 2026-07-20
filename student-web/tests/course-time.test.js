import { describe, expect, it } from 'vitest'
import { COURSE_PERIODS, courseMatchesSchedule, formatScheduleTime, periodToMinutes, scheduleMatchesPeriod } from '../src/utils/course-time'

describe('课程时间', () => {
  it('按 10 个一小时时段映射并支持星期/时段筛选', () => {
    expect(COURSE_PERIODS).toHaveLength(10)
    expect(periodToMinutes(1)).toBe(480)
    expect(periodToMinutes(4)).toBe(660)
    expect(periodToMinutes(5)).toBe(840)
    expect(periodToMinutes(10)).toBe(1200)
    const course = { schedules: [{ weekday: 2, start_minute: 540, end_minute: 600 }] }
    expect(courseMatchesSchedule(course, 2, 2)).toBe(true)
    expect(courseMatchesSchedule(course, 3, 2)).toBe(false)
    expect(scheduleMatchesPeriod(course.schedules[0], 3)).toBe(false)
    expect(formatScheduleTime(course.schedules[0])).toContain('第2节')
  })
})
