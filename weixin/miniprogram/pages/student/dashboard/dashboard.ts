import { navigationForRole } from '../../../domain/navigation'
import { enrollmentSummary } from '../../../domain/student-state'
import type { EnrollmentRecord, WaitlistRecord } from '../../../domain/types'
import { authService } from '../../../services/runtime'
import { studentService } from '../../../services/student'

Page({
  data: {
    phase: 'idle',
    user: authService.getUser(),
    navigation: navigationForRole('STUDENT'),
    summary: { enrolled: 0, conflictReview: 0, waiting: 0, terminal: 0 },
    error: '',
  },
  onShow() {
    try {
      this.setData({ user: authService.requireRole('STUDENT') })
      void this.load()
    } catch {
      wx.reLaunch({ url: '/pages/auth/login/login' })
    }
  },
  async load() {
    this.setData({ phase: 'loading', error: '' })
    try {
      const [enrollments, waitlists] = await Promise.all([
        studentService.listEnrollments(),
        studentService.listWaitlists(),
      ])
      this.setData({
        phase: 'data',
        summary: enrollmentSummary(enrollments.data as EnrollmentRecord[], waitlists.data as WaitlistRecord[]),
      })
    } catch (error) {
      this.setData({ phase: 'error', error: error instanceof Error ? error.message : '概览加载失败' })
    }
  },
  navigate(event: { currentTarget: { dataset: { url?: string } } }) {
    const url = event.currentTarget.dataset.url
    if (url && url !== '/pages/student/dashboard/dashboard') {
      wx.navigateTo({ url })
    }
  },
  logout() {
    authService.logout()
    wx.reLaunch({ url: '/pages/auth/login/login' })
  },
  retry() {
    void this.load()
  },
})
