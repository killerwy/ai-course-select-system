import { onBeforeUnmount, onMounted, ref } from 'vue'
import { errorMessage } from '../api/client'

export const DEFAULT_LIVE_REFRESH_MS = 5000

export function normalizeLiveInterval(intervalMs) {
  return Number.isFinite(intervalMs) ? Math.max(1000, intervalMs) : DEFAULT_LIVE_REFRESH_MS
}

export function useLiveQuery(loader, {
  initialValue = null,
  intervalMs = DEFAULT_LIVE_REFRESH_MS,
  errorFallback = '数据加载失败',
  isEmpty = value => value === null || value === undefined,
} = {}) {
  const data = ref(initialValue)
  const loading = ref(false)
  const refreshing = ref(false)
  const error = ref('')
  const lastSyncedAt = ref(null)
  let timer = null

  async function refresh({ silent = false } = {}) {
    if (loading.value || refreshing.value) return
    if (silent) refreshing.value = true
    else loading.value = true
    try {
      data.value = await loader()
      error.value = ''
      lastSyncedAt.value = new Date()
    } catch (cause) {
      // 轮询失败时保留上一份数据库快照；只有首次加载失败才阻断页面。
      if (isEmpty(data.value) || !silent) error.value = errorMessage(cause, errorFallback)
    } finally {
      loading.value = false
      refreshing.value = false
    }
  }

  function start() {
    void refresh()
    const safeInterval = normalizeLiveInterval(intervalMs)
    timer = setInterval(() => {
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return
      void refresh({ silent: true })
    }, safeInterval)
  }

  onMounted(start)
  onBeforeUnmount(() => {
    if (timer) clearInterval(timer)
    timer = null
  })

  return { data, loading, refreshing, error, lastSyncedAt, refresh }
}
