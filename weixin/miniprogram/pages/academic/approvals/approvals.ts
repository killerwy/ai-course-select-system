import type { CourseOperationRecord, ExceptionApprovalRecord } from '../../../domain/types'
import { canDecide } from '../../../domain/academic-view'
import { academicService } from '../../../services/academic'

Page({
  data: {
    phase: 'idle',
    mode: 'course',
    status: 'PENDING',
    operations: [] as CourseOperationRecord[],
    exceptions: [] as ExceptionApprovalRecord[],
    error: '',
  },
  onShow() {
    void this.load()
  },
  async load() {
    this.setData({ phase: 'loading', error: '' })
    try {
      if (this.data.mode === 'course') {
        const result = await academicService.listCourseOperations(this.data.status === 'ALL' ? undefined : this.data.status as 'PENDING' | 'APPROVED' | 'REJECTED')
        this.setData({ operations: result.data, phase: result.data.length ? 'data' : 'empty' })
      } else {
        const result = await academicService.listExceptionApprovals(this.data.status === 'ALL' ? undefined : this.data.status as 'PENDING' | 'APPROVED' | 'REJECTED')
        this.setData({ exceptions: result.data, phase: result.data.length ? 'data' : 'empty' })
      }
    } catch (error) {
      this.setData({ phase: 'error', error: error instanceof Error ? error.message : '审批加载失败' })
    }
  },
  switchMode(event: { currentTarget: { dataset: { mode: string } } }) {
    this.setData({ mode: event.currentTarget.dataset.mode }, () => { void this.load() })
  },
  async decide(event: { currentTarget: { dataset: { id: string; decision: 'approve' | 'reject'; type: string } } }) {
    const { id, decision, type } = event.currentTarget.dataset
    const ok = await new Promise<boolean>(resolve => wx.showModal({ title: decision === 'approve' ? '确认通过' : '确认驳回', content: '请确认已完成复核并提交决定。', success: value => resolve(value.confirm), fail: () => resolve(false) }))
    if (!ok) return
    try {
      if (type === 'course') await academicService.decideCourseOperation(id, decision, decision === 'approve' ? '教务复核通过' : '教务复核驳回')
      else await academicService.decideException(id, decision, decision === 'approve' ? '教务复核通过' : '教务复核驳回')
      wx.showToast({ title: '已提交', icon: 'success' })
      await this.load()
    } catch (error) {
      this.setData({ error: error instanceof Error ? error.message : '审批提交失败' })
    }
  },
  canDecide,
  retry() {
    void this.load()
  },
})
