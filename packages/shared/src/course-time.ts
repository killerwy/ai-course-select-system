export interface WeekdayOption {
  value: number
  label: string
}

export interface CoursePeriod {
  value: number
  start: number
  end: number
  time: string
  label: string
}

export interface CoursePeriodOption {
  value: number
  label: string
}

export const WEEKDAY_OPTIONS: readonly WeekdayOption[] = Object.freeze([
  { value: 1, label: '周一' },
  { value: 2, label: '周二' },
  { value: 3, label: '周三' },
  { value: 4, label: '周四' },
  { value: 5, label: '周五' },
  { value: 6, label: '周六' },
  { value: 7, label: '周日' },
])

export const COURSE_PERIODS: readonly CoursePeriod[] = Object.freeze([
  [1, 480, 540, '08:00-09:00'],
  [2, 540, 600, '09:00-10:00'],
  [3, 600, 660, '10:00-11:00'],
  [4, 660, 720, '11:00-12:00'],
  [5, 840, 900, '14:00-15:00'],
  [6, 900, 960, '15:00-16:00'],
  [7, 960, 1020, '16:00-17:00'],
  [8, 1020, 1080, '17:00-18:00'],
  [9, 1140, 1200, '19:00-20:00'],
  [10, 1200, 1260, '20:00-21:00'],
].map(([value, start, end, time]) =>
  Object.freeze({ value, start, end, time, label: `第${value}节` })
))

export const COURSE_PERIOD_OPTIONS: readonly CoursePeriodOption[] = Object.freeze(
  COURSE_PERIODS.map(({ value, label, time }) => ({
    value,
    label: `${label} ${time}`,
  }))
)

export function formatCourseTime(minutes: number): string {
  const value = Math.max(0, Number(minutes) || 0)
  return `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`
}

export function periodToMinutes(period: number): number {
  return COURSE_PERIODS.find(item => item.value === Number(period))?.start ?? NaN
}

export function minutesToPeriod(minutes: number): number | null {
  const value = Number(minutes)
  const exact = COURSE_PERIODS.find(item => item.start === value)
  if (exact) return exact.value
  const containing = COURSE_PERIODS.find(item => value >= item.start && value < item.end)
  return containing?.value ?? null
}

export interface ScheduleSlot {
  weekday?: number
  start_minute?: number
  end_minute?: number
  room?: string
}

export interface PeriodRange {
  first: CoursePeriod
  last: CoursePeriod
}

export function periodForSchedule(schedule: ScheduleSlot): PeriodRange | null {
  const start = Number(schedule?.start_minute)
  const end = Number(schedule?.end_minute)
  const first = COURSE_PERIODS.find(item => item.start === start)
  const last = COURSE_PERIODS.find(item => item.end === end)
  if (first && last) return { first, last }
  return null
}

export function formatScheduleTime(schedule: ScheduleSlot): string {
  const mapped = periodForSchedule(schedule)
  if (mapped) {
    const range = mapped.first.value === mapped.last.value
      ? mapped.first.label
      : `${mapped.first.label}-${mapped.last.label}`
    return `${range} ${mapped.first.time.split('-')[0]}-${mapped.last.time.split('-')[1]}`
  }
  return `${formatCourseTime(schedule?.start_minute ?? 0)}-${formatCourseTime(schedule?.end_minute ?? 0)}`
}

export function scheduleMatchesPeriod(schedule: ScheduleSlot, period: number): boolean {
  if (!period) return true
  const selected = COURSE_PERIODS.find(item => item.value === Number(period))
  if (!selected) return false
  const start = Number(schedule?.start_minute)
  const end = Number(schedule?.end_minute)
  return start < selected.end && end > selected.start
}

export interface CourseWithSchedules {
  schedules?: ScheduleSlot[]
}

export function courseMatchesSchedule(course: CourseWithSchedules, weekday: number, period: number): boolean {
  if (!weekday && !period) return true
  return (course?.schedules || []).some(schedule =>
    (!weekday || Number(schedule.weekday) === Number(weekday)) && scheduleMatchesPeriod(schedule, period)
  )
}
