import type { AuditRecord } from '../../../domain/types'
import { academicService } from '../../../services/academic'

Page({
  data: {
    phase: 'idle',
    logs: [] as AuditRecord[],
    courseId: '',
    runId: '',
    action: '',
    error: '',
  },
  onShow() {
    void this.load()
  },
  async load() {
    this.setData({ phase: 'loading', error: '' })
    try {
      const result = await academicService.listAuditLogs({ courseId: this.data.courseId || undefined, runId: this.data.runId || undefined, action: this.data.action || undefined })
      this.setData({ logs: result.data, phase: result.data.length ? 'data' : 'empty' })
    } catch (error) {
      this.setData({ phase: 'error', error: error instanceof Error ? error.message : '审计日志加载失败' })
    }
  },
  onInput(event: { currentTarget: { dataset: { field: string } }; detail: { value: string } }) {
    this.setData({ [event.currentTarget.dataset.field]: event.detail.value })
  },
  retry() {
    void this.load()
  },
})
