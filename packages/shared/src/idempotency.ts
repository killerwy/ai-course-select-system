export function createRequestId(scope = 'web'): string {
  const compactId = (value: string): string =>
    value.replace(/[^a-zA-Z0-9:_-]/g, '-').slice(0, 64)
  return compactId(`${scope}:${Date.now().toString(36)}:${Math.random().toString(36).slice(2, 10)}`)
}

export function createIdempotencyKey(scope: string, seed?: string): string {
  const compactId = (value: string): string =>
    value.replace(/[^a-zA-Z0-9:_-]/g, '-').slice(0, 64)
  const value = compactId(`${scope}:${seed ?? createRequestId('idem')}`)
  if (!value || value.length > 64) {
    throw new Error('INVALID_IDEMPOTENCY_KEY: 幂等键格式无效')
  }
  return value
}

export function idempotencyKey(prefix: string, value: string): string {
  const prefixPart = String(prefix || 'request').replace(/[^a-zA-Z0-9_-]/g, '').slice(0, 16)
  const valuePart = String(value || 'item').replace(/[^a-zA-Z0-9_-]/g, '').slice(-24)
  const timestampPart = Date.now().toString(36)
  const entropyPart = Math.random().toString(16).slice(2, 10)
  return `${prefixPart}-${valuePart}-${timestampPart}-${entropyPart}`
}
