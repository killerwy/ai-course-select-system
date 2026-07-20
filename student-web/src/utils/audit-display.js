const ACTION_LABELS = {
  COURSE_DELETED_BY_TEACHER: '教师删除课程',
  WAITLIST_PROMOTED: '候补通过',
  WAITLIST_SKIPPED: '候补暂未通过',
  EXCEPTION_APPROVED: '例外申请已批准',
  EXCEPTION_REJECTED: '例外申请已拒绝',
  ENROLLMENT_CREATED: '选课成功',
  ENROLLMENT_DROPPED: '已退课',
  WAITLIST_JOINED: '加入候补',
  WAITLIST_REMOVED: '退出候补',
}

export function auditActionLabel(action) {
  return ACTION_LABELS[action] || '学习记录变更'
}

function courseName(audit, course = null) {
  const after = audit?.after_json || {}
  const before = audit?.before_json || {}
  const code = after.course_code || before.course_code || course?.code
  const name = after.course_name || before.course_name || course?.name
  if (code && name) return `${code} ${name}`
  return code || name || after.course_id || before.course_id || audit?.resource_id || '未知课程'
}

export function auditDescription(audit, course = null) {
  const name = courseName(audit, course)
  if (audit?.action === 'COURSE_DELETED_BY_TEACHER') {
    const recordName = audit?.resource_type === 'waitlist_entry' ? '候补记录' : '选课记录'
    return `教师已删除课程《${name}》，你的${recordName}已关闭。`
  }
  if (audit?.action === 'WAITLIST_PROMOTED') return `课程《${name}》候补通过，已转为选课成功。`
  if (audit?.action === 'WAITLIST_SKIPPED') return `课程《${name}》本次暂未候补通过。`
  if (audit?.action === 'ENROLLMENT_CREATED') return `课程《${name}》选课成功。`
  if (audit?.action === 'ENROLLMENT_DROPPED') return `已退出课程《${name}》。`
  if (audit?.action === 'WAITLIST_JOINED') return `已加入课程《${name}》候补。`
  if (audit?.action === 'WAITLIST_REMOVED') return `已退出课程《${name}》候补。`
  return String(audit?.reason || `${auditActionLabel(audit?.action)}。`)
}
