const SENSITIVE_KEYS = /password|token|authorization|session[_-]?key|app[_-]?secret|secret|cookie|api[_-]?key/i

export function redactSensitive<T>(value: T): T {
  if (Array.isArray(value)) return value.map(item => redactSensitive(item)) as T
  if (value && typeof value === 'object') {
    const output: Record<string, unknown> = {}
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      output[key] = SENSITIVE_KEYS.test(key) ? '[REDACTED]' : redactSensitive(item)
    }
    return output as T
  }
  return value
}
