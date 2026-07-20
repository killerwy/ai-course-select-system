import type { RecalculationRun } from '../../../domain/types'
import { runProgress } from '../../../domain/academic-view'
import { academicService, pollRun } from '../../../services/academic'

Page({
  data: {
    phase: 'idle',
    run: undefined as RecalculationRun | undefined,
    runId: '',
    error: '',
    progress: '',
  },
  onLoad(options: { id?: string }) {
    this.setData({ runId: options.id || '' })
    void this.load()
  },
  async load() {
    if (!this.data.runId) {
      this.setData({ phase: 'error', error: '缺少重算批次编号' })
      return
    }
    this.setData({ phase: 'loading', error: '' })
    try {
      const result = await pollRun(runId => academicService.getRun(runId), this.data.runId, { attempts: 8, intervalMs: 1000 })
      this.setData({ run: result.data, progress: runProgress(result.data.status), phase: 'data' })
    } catch (error) {
      this.setData({ phase: 'error', error: error instanceof Error ? error.message : '重算批次加载失败' })
    }
  },
  retry() {
    void this.load()
  },
})
