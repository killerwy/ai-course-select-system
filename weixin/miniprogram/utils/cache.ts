export interface CacheEntry<T> {
  value: T
  savedAt: number
  staleAt: number
}

export interface ReadonlyCache<T> {
  read(): { value: T; stale: boolean } | undefined
  write(value: T): void
  clear(): void
}

export function createReadonlyCache<T>(storage: { get(key: string): unknown; set(key: string, value: unknown): void; remove(key: string): void }, key: string, ttlMs = 30_000): ReadonlyCache<T> {
  return {
    read() {
      const raw = storage.get(key) as Partial<CacheEntry<T>> | undefined
      if (!raw || typeof raw.savedAt !== 'number' || typeof raw.staleAt !== 'number' || !('value' in raw)) return undefined
      return { value: raw.value as T, stale: Date.now() >= raw.staleAt }
    },
    write(value) {
      const now = Date.now()
      storage.set(key, { value, savedAt: now, staleAt: now + ttlMs })
    },
    clear() {
      storage.remove(key)
    },
  }
}
