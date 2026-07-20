import type { CourseSchedule, CourseSummary, RecommendationSession, ScheduleItem } from './types'

export const SCHEDULE_WEEKDAYS = [
  { value: 1, label: '周一' },
  { value: 2, label: '周二' },
  { value: 3, label: '周三' },
  { value: 4, label: '周四' },
  { value: 5, label: '周五' },
  { value: 6, label: '周六' },
  { value: 7, label: '周日' },
] as const

export interface ScheduleGridLesson extends ScheduleItem {
  key: string
  display_name: string
  display_code?: string
  time: string
}

export interface ScheduleGridCell {
  weekday: number
  lessons: ScheduleGridLesson[]
}

export interface ScheduleGridRow {
  key: string
  time: string
  cells: ScheduleGridCell[]
}

export function formatSchedule(schedule: CourseSchedule): string {
  const weekday = ['日', '一', '二', '三', '四', '五', '六'][schedule.weekday % 7] ?? String(schedule.weekday)
  const pad = (value: number) => String(value).padStart(2, '0')
  const start = pad(Math.floor(schedule.start_minute / 60)) + ':' + pad(schedule.start_minute % 60)
  const end = pad(Math.floor(schedule.end_minute / 60)) + ':' + pad(schedule.end_minute % 60)
  return '周' + weekday + ' ' + start + '-' + end + ' · ' + schedule.room
}

function formatClock(minutes: number): string {
  const pad = (value: number) => String(value).padStart(2, '0')
  return pad(Math.floor(minutes / 60)) + ':' + pad(minutes % 60)
}

export function buildScheduleGrid(items: ScheduleItem[]): ScheduleGridRow[] {
  const validItems = items.filter(item => (
    Number.isInteger(item.weekday)
    && item.weekday >= 1
    && item.weekday <= 7
    && Number.isInteger(item.start_minute)
    && Number.isInteger(item.end_minute)
    && item.start_minute >= 0
    && item.end_minute > item.start_minute
  ))
  const lessons = validItems.map(item => ({
    ...item,
    key: [item.course_id, item.weekday, item.start_minute, item.end_minute, item.room].join(':'),
    display_name: item.course_name?.trim() || '未命名课程',
    display_code: item.course_code?.trim() || undefined,
    time: formatClock(item.start_minute) + '-' + formatClock(item.end_minute),
  }))
  const slotKeys = [...new Set(lessons.map(item => item.start_minute + ':' + item.end_minute))]
    .sort((left, right) => {
      const [leftStart, leftEnd] = left.split(':').map(Number)
      const [rightStart, rightEnd] = right.split(':').map(Number)
      return leftStart - rightStart || leftEnd - rightEnd
    })

  return slotKeys.map(slotKey => {
    const [start, end] = slotKey.split(':').map(Number)
    return {
      key: slotKey,
      time: formatClock(start) + '-' + formatClock(end),
      cells: SCHEDULE_WEEKDAYS.map(day => ({
        weekday: day.value,
        lessons: lessons.filter(item => item.weekday === day.value && item.start_minute === start && item.end_minute === end),
      })),
    }
  })
}

export function attachCourseLabels<T extends { course_id: string }>(records: T[], catalog: CourseSummary[]): Array<T & { course_name: string; course_code?: string }> {
  const byId = new Map(catalog.map(course => [course.id, course]))
  return records.map(record => {
    const course = byId.get(record.course_id)
    return {
      ...record,
      course_name: course?.name?.trim() || '未命名课程',
      course_code: course?.code?.trim() || undefined,
    }
  })
}

export function resolvePrerequisiteNames(ids: string[], catalog: CourseSummary[]): string[] {
  const byId = new Map(catalog.map(course => [course.id, course.name]))
  return ids.map(id => byId.get(id) ?? '未知先修（' + id + '）')
}

export function recommendationStatusText(session: RecommendationSession | undefined): string {
  if (!session) return ''
  return session.status === 'FALLBACK' ? '外部推荐不可用，当前为规则兜底结果' : session.status === 'COMPLETED' ? '推荐已完成，资格仍以提交时服务端检查为准' : '推荐处理中'
}
