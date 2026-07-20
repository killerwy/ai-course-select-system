import type { CourseSummary } from './types'
import type { CourseWritePayload } from '../services/academic'

export function validateCourseWrite(payload: Partial<CourseWritePayload>): string[] {
  const errors: string[] = []
  if (!payload.code?.trim()) errors.push('课程代码不能为空')
  if (!payload.name?.trim()) errors.push('课程名称不能为空')
  if (!payload.teacher_name?.trim()) errors.push('教师姓名不能为空')
  if (!Number.isFinite(payload.credits) || (payload.credits ?? 0) <= 0) errors.push('学分必须大于 0')
  if (!Number.isFinite(payload.capacity) || (payload.capacity ?? 0) <= 0) errors.push('容量必须大于 0')
  if (!Array.isArray(payload.schedules) || payload.schedules.length === 0) errors.push('至少填写一段上课时间')
  for (const schedule of payload.schedules ?? []) {
    if (schedule.weekday < 1 || schedule.weekday > 7 || schedule.start_minute >= schedule.end_minute) {
      errors.push('上课时间范围无效')
      break
    }
    if (!schedule.room?.trim()) {
      errors.push('教室不能为空')
      break
    }
  }
  return errors
}

export function canDecide(status: unknown): boolean {
  return status === 'PENDING'
}

export function runProgress(status: unknown): string {
  if (status === 'PENDING') return '排队中'
  if (status === 'RUNNING') return '重算中'
  if (status === 'SUCCEEDED') return '已完成'
  if (status === 'FAILED') return '失败，可查看错误后重试'
  return '未知状态'
}

export function courseDisplay(course: CourseSummary): string {
  return `${course.code} · ${course.name} · ${course.teacher_name}`
}
