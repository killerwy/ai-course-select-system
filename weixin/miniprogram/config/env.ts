export interface ApiEnvironment {
  apiBaseUrl: string
  timeoutMs: number
  pollingIntervalMs: number
  maxPollingAttempts: number
}

export const API_BASE_URL_STORAGE_KEY = 'courseflow.apiBaseUrl'

export const DEVELOPMENT_ENV: Readonly<ApiEnvironment> = {
  // DevTools local simulator can reach this backend. Real devices require an
  // HTTPS request domain configured in WeChat admin and should use the runtime
  // override or a release-specific value below.
  apiBaseUrl: 'http://127.0.0.1:8000/api/v1',
  timeoutMs: 10000,
  pollingIntervalMs: 1500,
  maxPollingAttempts: 30,
}

export const WECHAT_API_ENVIRONMENTS: Readonly<Record<'develop' | 'trial' | 'release', string>> = {
  develop: DEVELOPMENT_ENV.apiBaseUrl,
  trial: DEVELOPMENT_ENV.apiBaseUrl,
  release: DEVELOPMENT_ENV.apiBaseUrl,
}

export function normalizeBaseUrl(value: string): string {
  const normalized = value.trim().replace(/\/+$/, '')
  if (!/^https?:\/\//.test(normalized)) {
    throw new Error('API_BASE_URL_INVALID')
  }
  return normalized
}

function accountEnvironment(): 'develop' | 'trial' | 'release' | undefined {
  try {
    if (typeof wx === 'undefined') return undefined
    const accountApi = wx as unknown as { getAccountInfoSync?: () => { miniProgram?: { envVersion?: string } } }
    if (typeof accountApi.getAccountInfoSync !== 'function') return undefined
    const envVersion = accountApi.getAccountInfoSync()?.miniProgram?.envVersion
    return envVersion === 'trial' || envVersion === 'release' || envVersion === 'develop' ? envVersion : undefined
  } catch {
    return undefined
  }
}

/**
 * Resolve the backend endpoint once at app startup. A storage override is
 * deliberately explicit so DevTools can point to an HTTPS tunnel without
 * changing business code; it is never sent to the backend as user data.
 */
export function resolveApiBaseUrl(): string {
  let override = ''
  try {
    if (typeof wx !== 'undefined' && typeof wx.getStorageSync === 'function') {
      const value = wx.getStorageSync(API_BASE_URL_STORAGE_KEY)
      override = typeof value === 'string' ? value.trim() : ''
    }
  } catch {
    override = ''
  }
  const env = accountEnvironment() ?? 'develop'
  return normalizeBaseUrl(override || WECHAT_API_ENVIRONMENTS[env])
}
