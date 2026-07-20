import { enrolledSchedule } from '../../../domain/student-state'
import { buildScheduleGrid, SCHEDULE_WEEKDAYS } from '../../../domain/student-view'
import type { ScheduleItem } from '../../../domain/types'
import { studentService } from '../../../services/student'

Page({
  data: {
    phase: 'idle',
    items: [] as Array<ScheduleItem & { key: string; label: string }>,
    weekdays: SCHEDULE_WEEKDAYS,
    rows: [] as ReturnType<typeof buildScheduleGrid>,
    error: '',
  },
  onShow() {
    void this.load()
  },
  async load() {
    this.setData({ phase: 'loading', error: '' })
    try {
      const result = await studentService.getSchedule()
      const items = enrolledSchedule(result.data.courses).map(item => ({
        ...item,
        key: [item.course_id, item.weekday, item.start_minute, item.end_minute].join(':'),
        label: item.course_name || '未命名课程',
      }))
      this.setData({ phase: items.length ? 'data' : 'empty', items, rows: buildScheduleGrid(items) })
    } catch (error) {
      this.setData({ phase: 'error', error: error instanceof Error ? error.message : '课程表加载失败' })
    }
  },
  retry() {
    void this.load()
  },
})
