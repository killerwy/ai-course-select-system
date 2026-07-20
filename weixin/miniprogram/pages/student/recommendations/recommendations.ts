import { recommendationStatusText } from '../../../domain/student-view'
import type { RecommendationSession } from '../../../domain/types'
import { ApiError } from '../../../services/http'
import { studentService } from '../../../services/student'

Page({
  data: {
    phase: 'idle',
    goals: '',
    preferences: '',
    session: undefined as RecommendationSession | undefined,
    statusText: '',
    error: '',
    busy: false,
  },
  onInput(event: { currentTarget: { dataset: { field: 'goals' | 'preferences' } }; detail: { value: string } }) {
    this.setData({ [event.currentTarget.dataset.field]: event.detail.value })
  },
  async submit() {
    if (this.data.busy) return
    const goals = this.data.goals.trim()
    if (!goals) {
      this.setData({ error: '请填写学习目标' })
      return
    }
    const preferences = this.data.preferences.split(',').map(item => item.trim()).filter(Boolean)
    this.setData({ busy: true, phase: 'loading', error: '' })
    try {
      const result = await studentService.createRecommendations({ goals, preferences })
      this.setData({
        phase: result.data.items.length ? 'data' : 'empty',
        session: result.data,
        statusText: recommendationStatusText(result.data),
      })
    } catch (error) {
      this.setData({
        phase: 'error',
        error: error instanceof ApiError ? error.message : '推荐请求失败',
      })
    } finally {
      this.setData({ busy: false })
    }
  },
  openCourse(event: { currentTarget: { dataset: { id: string } } }) {
    wx.navigateTo({ url: '/pages/student/course-detail/course-detail?id=' + encodeURIComponent(event.currentTarget.dataset.id) })
  },
  retry() {
    void this.submit()
  },
})
