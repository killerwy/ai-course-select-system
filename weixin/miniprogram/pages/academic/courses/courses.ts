import type { CourseSummary } from '../../../domain/types'
import { academicService } from '../../../services/academic'
import { ApiError } from '../../../services/http'

Page({
  data: {
    phase: 'idle',
    courses: [] as CourseSummary[],
    keyword: '',
    status: '',
    error: '',
    stale: false,
    createCode: '',
    createName: '',
    createTeacher: '',
    createCapacity: '30',
    statuses: ['全部', 'OPEN', 'PENDING_APPROVAL', 'CLOSED', 'CANCELLED'],
  },
  onShow() {
    void this.load()
  },
  async load() {
    this.setData({ phase: 'loading', error: '' })
    try {
      const result = await academicService.listCourses({ keyword: this.data.keyword, status: this.data.status || undefined })
      this.setData({ courses: result.data, phase: result.data.length ? 'data' : 'empty', stale: false })
    } catch (error) {
      this.setData({ phase: this.data.courses.length ? 'data' : 'error', stale: this.data.courses.length > 0, error: error instanceof Error ? error.message : '课程加载失败' })
    }
  },
  onKeywordInput(event: { detail: { value: string } }) {
    this.setData({ keyword: event.detail.value })
  },
  onStatusChange(event: { detail: { value: string } }) {
    const index = Number(event.detail.value)
    this.setData({ status: index === 0 ? '' : this.data.statuses[index] }, () => { void this.load() })
  },
  onCreateInput(event: { currentTarget: { dataset: { field: string } }; detail: { value: string } }) {
    const field = event.currentTarget.dataset.field
    this.setData({ [field]: event.detail.value })
  },
  async createCourse() {
    const { createCode, createName, createTeacher, createCapacity } = this.data
    if (!createCode || !createName || !createTeacher) {
      this.setData({ error: '请填写课程代码、名称和教师' })
      return
    }
    const confirmed = await new Promise<boolean>(resolve => wx.showModal({
      title: 'Confirm submit',
      content: 'The course will remain pending until approved.',
      success: value => resolve(value.confirm),
      fail: () => resolve(false),
    }))
    if (!confirmed) return
    try {
      await academicService.createCourse({
        code: createCode,
        name: createName,
        teacher_name: createTeacher,
        credits: 3,
        capacity: Math.max(1, Number(createCapacity) || 30),
        schedules: [{ weekday: 1, start_minute: 480, end_minute: 570, room: '待安排' }],
        prerequisites: [],
      })
      wx.showToast({ title: '已提交审批', icon: 'success' })
      this.setData({ createCode: '', createName: '', createTeacher: '' })
      await this.load()
    } catch (error) {
      this.setData({ error: error instanceof ApiError ? error.message : '提交失败' })
    }
  },
  openRun(event: { currentTarget: { dataset: { id: string } } }) {
    wx.navigateTo({ url: '/pages/academic/run-detail/run-detail?id=' + encodeURIComponent(event.currentTarget.dataset.id) })
  },
  async action(event: { currentTarget: { dataset: { id: string; action: string } } }) {
    const course = this.data.courses.find(item => item.id === event.currentTarget.dataset.id)
    if (!course) return
    const action = event.currentTarget.dataset.action
    const confirmed = await new Promise<boolean>(resolve => wx.showModal({
      title: 'Confirm operation',
      content: 'This changes shared course state. Continue?',
      success: value => resolve(value.confirm),
      fail: () => resolve(false),
    }))
    if (!confirmed) return
    try {
      let result: { data: unknown } | undefined
      if (action === 'expand') result = await academicService.expandCourse(course.id, 5, course.version)
      if (action === 'reschedule') result = await academicService.rescheduleCourse(course.id, [{ weekday: 2, start_minute: 480, end_minute: 570, room: '待安排' }], course.version)
      if (action === 'cancel') result = await academicService.cancelCourse(course.id, '教务端操作', course.version)
      if (action === 'recalculate') result = await academicService.startRecalculation(course.id, course.version)
      if (result) {
        const value = result.data as { run?: { id?: string } }
        wx.showToast({ title: action === 'cancel' ? '已提交审批' : '操作已提交', icon: 'success' })
        if (value.run?.id) wx.navigateTo({ url: '/pages/academic/run-detail/run-detail?id=' + encodeURIComponent(value.run.id) })
        await this.load()
      }
    } catch (error) {
      this.setData({ error: error instanceof Error ? error.message : '操作失败' })
    }
  },
  retry() {
    void this.load()
  },
})
