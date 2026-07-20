import { resolvePrerequisiteNames, formatSchedule } from '../../../domain/student-view'
import type { CourseSummary } from '../../../domain/types'
import { ApiError } from '../../../services/http'
import { studentService } from '../../../services/student'

Page({
  data: {
    phase: 'idle',
    course: undefined as CourseSummary | undefined,
    prerequisites: [] as string[],
    scheduleText: [] as string[],
    courseId: '',
    busy: false,
    error: '',
  },
  onLoad(options: { id?: string }) {
    const courseId = options.id ?? ''
    this.setData({ courseId })
    void this.load()
  },
  async load() {
    if (!this.data.courseId) {
      this.setData({ phase: 'error', error: '缺少课程编号' })
      return
    }
    this.setData({ phase: 'loading', error: '' })
    try {
      const [detail, catalog] = await Promise.all([
        studentService.getCourse(this.data.courseId),
        studentService.listCourses(),
      ])
      this.setData({
        phase: 'data',
        course: detail.data,
        prerequisites: resolvePrerequisiteNames(detail.data.prerequisites, catalog.data),
        scheduleText: detail.data.schedules.map(formatSchedule),
      })
    } catch (error) {
      this.setData({ phase: 'error', error: error instanceof Error ? error.message : '课程详情加载失败' })
    }
  },
  async requestEnrollment(event: { currentTarget: { dataset: { type: 'ENROLL' | 'WAITLIST' | 'DROP' } } }) {
    if (this.data.busy || !this.data.course) return
    const type = event.currentTarget.dataset.type
    const labels = { ENROLL: '选课', WAITLIST: '加入候补', DROP: '退课' }
    const confirm = await new Promise<boolean>(resolve => {
      wx.showModal({
        title: labels[type] + '确认',
        content: '结果将以服务端状态为准，是否继续？',
        success: result => resolve(result.confirm),
        fail: () => resolve(false),
      })
    })
    if (!confirm) return
    this.setData({ busy: true, error: '' })
    try {
      await studentService.requestEnrollment(this.data.course.id, type)
      wx.showToast({ title: '请求已提交', icon: 'success' })
      await this.load()
    } catch (error) {
      const message = error instanceof ApiError ? error.message : '请求失败，请稍后重试'
      this.setData({ error: message })
    } finally {
      this.setData({ busy: false })
    }
  },
  retry() {
    void this.load()
  },
})
