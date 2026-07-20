import type { AuditRecord, EnrollmentRecord, ScheduleItem, WaitlistRecord } from './types'

export function enrollmentSummary(enrollments: EnrollmentRecord[], waitlists: WaitlistRecord[]) {
  return {
    enrolled: enrollments.filter(item => item.status === 'ENROLLED').length,
    conflictReview: enrollments.filter(item => item.status === 'CONFLICT_REVIEW').length,
    waiting: waitlists.filter(item => item.status === 'WAITING').length,
    terminal: enrollments.filter(item => ['DROPPED', 'CANCELLED_BY_ADMIN'].includes(item.status)).length,
  }
}

export function enrolledSchedule(items: ScheduleItem[]): ScheduleItem[] {
  return items.filter(item => item.status === 'ENROLLED' || item.status === 'CONFLICT_REVIEW')
}

export function ownAuditLogs(logs: AuditRecord[], userId: string): AuditRecord[] {
  return logs.filter(item => item.actor_id === userId || item.subject_student_id === userId)
}
