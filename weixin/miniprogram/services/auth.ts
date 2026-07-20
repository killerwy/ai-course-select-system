import { isRecord, isRole } from '../domain/guards'
import type { LoginResponse, Role, UserSummary } from '../domain/types'
import { ApiError, type HttpResult } from './http'

export const SESSION_STORAGE_KEY = 'courseflow.session.v1'
const DEFAULT_SESSION_TTL_MS = 8 * 60 * 60 * 1000

export interface Session {
  accessToken: string
  user: UserSummary
  expiresAt: number
}

export interface StorageAdapter {
  get(key: string): unknown
  set(key: string, value: unknown): void
  remove(key: string): void
}

export interface AuthClient {
  request<T>(path: string, options?: {
    method?: 'GET' | 'POST'
    data?: unknown
    requiresAuth?: boolean
  }): Promise<HttpResult<T>>
}

export interface Credentials {
  username: string
  password: string
}

export interface RegisterPayload extends Credentials {
  student_no: string
  major: string
  grade: number
}

export function createWxStorage(): StorageAdapter {
  return {
    get: key => wx.getStorageSync(key),
    set: (key, value) => wx.setStorageSync(key, value),
    remove: key => wx.removeStorageSync(key),
  }
}

function isUserSummary(value: unknown): value is UserSummary {
  return isRecord(value)
    && typeof value.id === 'string'
    && value.id.length > 0
    && typeof value.username === 'string'
    && value.username.length > 0
    && isRole(value.role)
}

function parseSession(value: unknown, now: number): Session | undefined {
  if (!isRecord(value)
    || typeof value.accessToken !== 'string'
    || value.accessToken.length === 0
    || !isUserSummary(value.user)
    || typeof value.expiresAt !== 'number'
    || value.expiresAt <= now) {
    return undefined
  }
  return {
    accessToken: value.accessToken,
    user: value.user,
    expiresAt: value.expiresAt,
  }
}

function parseLogin(value: unknown): LoginResponse {
  if (!isRecord(value)
    || typeof value.access_token !== 'string'
    || value.access_token.length === 0
    || value.token_type !== 'bearer'
    || !isUserSummary(value.user)) {
    throw new ApiError({ code: 'INVALID_LOGIN_RESPONSE', message: '登录响应格式无效' })
  }
  return value as unknown as LoginResponse
}

export function createSessionStore(storage: StorageAdapter = createWxStorage(), now = () => Date.now()) {
  let current: Session | undefined

  function load(): Session | undefined {
    const parsed = parseSession(storage.get(SESSION_STORAGE_KEY), now())
    if (!parsed) {
      storage.remove(SESSION_STORAGE_KEY)
      current = undefined
      return undefined
    }
    current = parsed
    return parsed
  }

  function save(login: LoginResponse, ttlMs = DEFAULT_SESSION_TTL_MS): Session {
    const session: Session = {
      accessToken: login.access_token,
      user: login.user,
      expiresAt: now() + ttlMs,
    }
    storage.set(SESSION_STORAGE_KEY, session)
    current = session
    return session
  }

  function replaceUser(user: UserSummary): Session | undefined {
    const session = current ?? load()
    if (!session) return undefined
    const next = { ...session, user }
    storage.set(SESSION_STORAGE_KEY, next)
    current = next
    return next
  }

  function clear(): void {
    current = undefined
    storage.remove(SESSION_STORAGE_KEY)
  }

  return {
    load,
    save,
    replaceUser,
    clear,
    getSession: () => current,
    getAccessToken: () => (current ?? load())?.accessToken,
    getUser: () => (current ?? load())?.user,
  }
}

export function createAuthService(
  client: AuthClient,
  store: ReturnType<typeof createSessionStore>,
) {
  function ensureRole(user: UserSummary, expectedRole?: Role): void {
    if (expectedRole && user.role !== expectedRole) {
      store.clear()
      throw new ApiError({
        code: 'ROLE_MISMATCH',
        message: expectedRole === 'STUDENT' ? '该账号不是学生账号' : '该账号不是教务账号',
        statusCode: 403,
      })
    }
  }

  async function login(credentials: Credentials, expectedRole?: Role): Promise<Session> {
    const result = await client.request<LoginResponse>('/auth/login', {
      method: 'POST',
      data: credentials,
      requiresAuth: false,
    })
    const loginResponse = parseLogin(result.data)
    ensureRole(loginResponse.user, expectedRole)
    return store.save(loginResponse)
  }

  async function register(payload: RegisterPayload): Promise<Session> {
    const result = await client.request<LoginResponse>('/auth/register', {
      method: 'POST',
      data: payload,
      requiresAuth: false,
    })
    const loginResponse = parseLogin(result.data)
    ensureRole(loginResponse.user, 'STUDENT')
    return store.save(loginResponse)
  }

  async function restore(expectedRole?: Role): Promise<Session | undefined> {
    const cached = store.load()
    if (!cached) return undefined
    try {
      const result = await client.request<UserSummary>('/me')
      if (!isUserSummary(result.data)) {
        throw new ApiError({ code: 'INVALID_ME_RESPONSE', message: '用户信息响应格式无效' })
      }
      ensureRole(result.data, expectedRole)
      return store.replaceUser(result.data)
    } catch (error) {
      store.clear()
      throw error
    }
  }

  function requireRole(role: Role): UserSummary {
    const user = store.getUser()
    if (!user) {
      throw new ApiError({ code: 'UNAUTHORIZED', message: '请先登录', statusCode: 401 })
    }
    ensureRole(user, role)
    return user
  }

  return {
    login,
    register,
    restore,
    logout: store.clear,
    requireRole,
    getSession: store.getSession,
    getUser: store.getUser,
  }
}
