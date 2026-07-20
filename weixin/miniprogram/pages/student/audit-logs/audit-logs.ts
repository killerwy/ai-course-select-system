import { ownAuditLogs } from '../../../domain/student-state'
import type { AuditRecord } from '../../../domain/types'
import { authService } from '../../../services/runtime'
import { studentService } from '../../../services/student'

Page({
  data: {
    phase: 'idle',
    logs: [] as AuditRecord[],
    error: '',
  },
  onShow() {
    void this.load()
  },
  async load() {
    this.setData({ phase: 'loading', error: '' })
    try {
      const result = await studentService.listAuditLogs()
      const userId = authService.getUser()?.id ?? ''
      const logs = ownAuditLogs(result.data, userId)
      this.setData({ phase: logs.length ? 'data' : 'empty', logs })
    } catch (error) {
      this.setData({ phase: 'error', error: error instanceof Error ? error.message : '审计加载失败' })
    }
  },
  retry() {
    void this.load()
  },
})
