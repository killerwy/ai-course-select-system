import test from 'node:test'
import assert from 'node:assert/strict'

import { attachCourseLabels, buildScheduleGrid, formatSchedule, recommendationStatusText, resolvePrerequisiteNames, SCHEDULE_WEEKDAYS } from '../miniprogram/domain/student-view.ts'

test('MP-07 normal: formats schedule and resolves known prerequisites', () => {
  const schedule = formatSchedule({ weekday: 1, start_minute: 540, end_minute: 630, room: 'A-101' })
  assert.equal(schedule, '周一 09:00-10:30 · A-101')
  assert.deepEqual(
    resolvePrerequisiteNames(['course-101'], [{ id: 'course-101', name: '程序设计基础' }]),
    ['程序设计基础'],
  )
})

test('MP-07 boundary: unknown prerequisite remains diagnosable', () => {
  assert.deepEqual(resolvePrerequisiteNames(['missing-id'], []), ['未知先修（missing-id）'])
})

test('MP-08 status: fallback is explicit and not treated as completed', () => {
  assert.equal(recommendationStatusText({ id: 's', status: 'FALLBACK', items: [] }), '外部推荐不可用，当前为规则兜底结果')
  assert.equal(recommendationStatusText({ id: 's', status: 'COMPLETED', items: [] }).includes('资格'), true)
})

test('MP-27 schedule grid: renders weekdays and course names instead of IDs', () => {
  assert.deepEqual(SCHEDULE_WEEKDAYS.map(day => day.label), ['周一', '周二', '周三', '周四', '周五', '周六', '周日'])
  const rows = buildScheduleGrid([
    { course_id: 'course-1', course_code: 'CS101', course_name: '软件工程实践', teacher_name: '李老师', status: 'ENROLLED', weekday: 1, start_minute: 540, end_minute: 630, room: 'A-101' },
    { course_id: 'course-2', course_code: 'AI202', course_name: '机器学习', teacher_name: '王老师', status: 'CONFLICT_REVIEW', weekday: 3, start_minute: 540, end_minute: 630, room: 'B-201' },
  ])
  assert.equal(rows.length, 1)
  assert.equal(rows[0].time, '09:00-10:30')
  assert.deepEqual(rows[0].cells.map(cell => cell.lessons.map(lesson => lesson.display_name)), [
    ['软件工程实践'], [], ['机器学习'], [], [], [], [],
  ])
  assert.equal(rows[0].cells[0].lessons[0].display_name.includes('course-1'), false)
})

test('MP-27 schedule grid: rejects invalid slots and supplies a safe name fallback', () => {
  const rows = buildScheduleGrid([
    { course_id: 'course-1', status: 'ENROLLED', weekday: 0, start_minute: 540, end_minute: 630, room: 'A' },
    { course_id: 'course-2', status: 'ENROLLED', weekday: 2, start_minute: 630, end_minute: 600, room: 'B' },
    { course_id: 'course-3', status: 'ENROLLED', weekday: 7, start_minute: 600, end_minute: 660, room: 'C' },
  ])
  assert.equal(rows.length, 1)
  assert.equal(rows[0].cells[6].lessons[0].display_name, '未命名课程')
})

test('MP-28 enrollment labels: resolves course names without exposing course IDs', () => {
  const labeled = attachCourseLabels(
    [{ course_id: 'course-1', status: 'ENROLLED' }],
    [{ id: 'course-1', code: 'CS101', name: '软件工程实践' }],
  )
  assert.equal(labeled[0].course_name, '软件工程实践')
  assert.equal(labeled[0].course_code, 'CS101')
  assert.equal(labeled[0].course_name.includes('course-1'), false)
  assert.equal(attachCourseLabels([{ course_id: 'missing' }], [])[0].course_name, '未命名课程')
})
