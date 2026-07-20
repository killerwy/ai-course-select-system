import { enrollmentSummary } from '../../../domain/student-state'
import { attachCourseLabels } from '../../../domain/student-view'
import type { CourseSummary, EnrollmentRecord, WaitlistRecord } from '../../../domain/types'
import { ApiError } from '../../../services/http'
import { studentService } from '../../../services/student'

Page({
  data: {
    phase: 'idle',
    enrollments: [] as EnrollmentRecord[],
    waitlists: [] as WaitlistRecord[],
    summary: { enrolled: 0, conflictReview: 0, waiting: 0, terminal: 0 },
    busyId: '',
    error: '',
  },
  onShow() {
    void this.load()
  },
  async load() {
    this.setData({ phase: 'loading', error: '' })
    try {
      const [enrollments, waitlists] = await Promise.all([
        studentService.listEnrollments(),
        studentService.listWaitlists(),
      ])
      let catalog: CourseSummary[] = []
      try {
        catalog = (await studentService.listCourses()).data
      } catch {
        // Course labels are best-effort; enrollment state remains authoritative.
      }
      this.setData({
        phase: enrollments.data.length || waitlists.data.length ? 'data' : 'empty',
        enrollments: attachCourseLabels(enrollments.data, catalog),
        waitlists: attachCourseLabels(waitlists.data, catalog),
        summary: enrollmentSummary(enrollments.data, waitlists.data),
      })
    } catch (error) {
      this.setData({ phase: 'error', error: error instanceof Error ? error.message : '选课记录加载失败' })
    }
  },
  async request(event: { currentTarget: { dataset: { id: string; type: 'DROP' } } }) {
    const id = event.currentTarget.dataset.id
    if (this.data.busyId) return
    this.setData({ busyId: id, error: '' })
    try {
      await studentService.requestEnrollment(id, 'DROP')
      wx.showToast({ title: '操作已提交', icon: 'success' })
      await this.load()
    } catch (error) {
      this.setData({ error: error instanceof ApiError ? error.message : '操作失败' })
    } finally {
      this.setData({ busyId: '' })
    }
  },
  retry() {
    void this.load()
  },
})
