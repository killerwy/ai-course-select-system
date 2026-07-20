import { describe, expect, it } from 'vitest'
import { auditActionLabel, auditDescription } from '../src/utils/audit-display'

describe('审计展示', () => {
  it('学生审计中心用中文提示教师删除了课程', () => {
    const audit = {
      action: 'COURSE_DELETED_BY_TEACHER',
      resource_type: 'enrollment',
      resource_id: 'enrollment-001',
      before_json: { course_id: 'course-201', course_code: 'AI201', course_name: '人工智能导论', status: 'ENROLLED' },
      after_json: { course_id: 'course-201', course_code: 'AI201', course_name: '人工智能导论', status: 'CANCELLED_BY_ADMIN' },
      reason: '教师已删除课程《人工智能导论》',
    }
    expect(auditActionLabel(audit.action)).toBe('教师删除课程')
    expect(auditDescription(audit)).toBe('教师已删除课程《AI201 人工智能导论》，你的选课记录已关闭。')
  })

  it('旧审计记录通过课程目录补全课程编码和名称', () => {
    const audit = {
      action: 'WAITLIST_PROMOTED',
      resource_type: 'waitlist_entry',
      before_json: { course_id: 'course-201', status: 'WAITING' },
      after_json: { course_id: 'course-201', status: 'PROMOTED' },
    }
    const course = { id: 'course-201', code: 'AI201', name: '人工智能导论' }
    expect(auditDescription(audit, course)).toBe('课程《AI201 人工智能导论》候补通过，已转为选课成功。')
    expect(auditDescription({ action: 'ENROLLMENT_CREATED', resource_id: 'course-201' }, course)).toBe('课程《AI201 人工智能导论》选课成功。')
  })
})
