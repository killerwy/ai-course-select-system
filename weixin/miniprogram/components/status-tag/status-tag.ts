import { statusLabel } from '../../domain/guards'

Component({
  properties: {
    status: {
      type: String,
      value: '',
      observer(value: string) {
        this.setData({ label: statusLabel(value) })
      },
    },
  },
  data: {
    label: '未知',
  },
})
