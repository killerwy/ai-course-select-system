import type { Role } from './types'

export interface NavigationItem {
  label: string
  url: string
  roles: readonly Role[]
}

export const STUDENT_HOME = '/pages/student/dashboard/dashboard'
export const ACADEMIC_HOME = '/pages/academic/courses/courses'
export const LOGIN_PAGE = '/pages/auth/login/login'

export const NAVIGATION_ITEMS: readonly NavigationItem[] = [
  { label: '课程目录', url: '/pages/student/courses/courses', roles: ['STUDENT'] },
  { label: '智能推荐', url: '/pages/student/recommendations/recommendations', roles: ['STUDENT'] },
  { label: '我的选课', url: '/pages/student/enrollments/enrollments', roles: ['STUDENT'] },
  { label: '课程表', url: '/pages/student/schedule/schedule', roles: ['STUDENT'] },
  { label: '我的审计', url: '/pages/student/audit-logs/audit-logs', roles: ['STUDENT'] },
  { label: '课程管理', url: ACADEMIC_HOME, roles: ['ACADEMIC'] },
  { label: '审批中心', url: '/pages/academic/approvals/approvals', roles: ['ACADEMIC'] },
  { label: '教务审计', url: '/pages/academic/audit-logs/audit-logs', roles: ['ACADEMIC'] },
]

export function homeForRole(role: Role): string {
  return role === 'STUDENT' ? STUDENT_HOME : ACADEMIC_HOME
}

export function navigationForRole(role: Role): NavigationItem[] {
  return NAVIGATION_ITEMS.filter(item => item.roles.includes(role))
}

export function routeAllowed(url: string, role: Role): boolean {
  const item = NAVIGATION_ITEMS.find(candidate => candidate.url === url)
  return item ? item.roles.includes(role) : false
}
