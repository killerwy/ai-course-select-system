import { filterCourseList, studentService } from '../../../services/student'
import type { CourseSummary } from '../../../domain/types'

Page({
  data: {
    phase: 'idle',
    courses: [] as CourseSummary[],
    visibleCourses: [] as CourseSummary[],
    keyword: '',
    status: '',
    weekday: 0,
    period: 0,
    stale: false,
    error: '',
    statuses: ['全部', 'OPEN', 'PENDING_APPROVAL', 'CLOSED', 'CANCELLED'],
    weekdays: ['全部', '周一', '周二', '周三', '周四', '周五', '周六', '周日'],
    periods: ['全部', '第1节', '第2节', '第3节', '第4节', '第5节', '第6节', '第7节', '第8节', '第9节', '第10节'],
  },
  refreshTimer: undefined as number | undefined,
  onShow() {
    void this.load(false)
    this.refreshTimer = setInterval(() => { void this.load(true) }, 5000) as unknown as number
  },
  onHide() {
    if (this.refreshTimer !== undefined) clearInterval(this.refreshTimer)
    this.refreshTimer = undefined
  },
  async load(silent: boolean) {
    if (!silent && this.data.phase === 'loading') return
    if (!silent) this.setData({ phase: 'loading', error: '' })
    try {
      const result = await studentService.listCourses({ keyword: this.data.keyword, status: this.data.status || undefined })
      const visibleCourses = filterCourseList(result.data, this.data)
      this.setData({
        phase: visibleCourses.length ? 'data' : 'empty',
        courses: result.data,
        visibleCourses,
        stale: false,
        error: '',
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : '课程加载失败'
      this.setData({
        phase: this.data.courses.length ? 'data' : 'error',
        stale: this.data.courses.length > 0,
        error: message,
      })
    }
  },
  applyFilters() {
    const visibleCourses = filterCourseList(this.data.courses, this.data)
    this.setData({ visibleCourses, phase: visibleCourses.length ? 'data' : 'empty' })
  },
  onKeywordInput(event: { detail: { value: string } }) {
    this.setData({ keyword: event.detail.value }, () => this.applyFilters())
  },
  onStatusChange(event: { detail: { value: string } }) {
    const index = Number(event.detail.value)
    this.setData({ status: index === 0 ? '' : this.data.statuses[index] }, () => this.applyFilters())
  },
  onWeekdayChange(event: { detail: { value: string } }) {
    this.setData({ weekday: Number(event.detail.value) }, () => this.applyFilters())
  },
  onPeriodChange(event: { detail: { value: string } }) {
    this.setData({ period: Number(event.detail.value) }, () => this.applyFilters())
  },
  openDetail(event: { currentTarget: { dataset: { id: string } } }) {
    wx.navigateTo({ url: '/pages/student/course-detail/course-detail?id=' + encodeURIComponent(event.currentTarget.dataset.id) })
  },
  retry() {
    void this.load(false)
  },
})
