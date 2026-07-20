Component({
  properties: {
    phase: {
      type: String,
      value: 'idle',
    },
    message: {
      type: String,
      value: '',
    },
    stale: {
      type: Boolean,
      value: false,
    },
  },
  methods: {
    retry() {
      this.triggerEvent('retry')
    },
  },
})

