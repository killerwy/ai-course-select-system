import { createAuthService, createSessionStore } from './auth'
import { createApiClient } from './http'
import { resolveApiBaseUrl } from '../config/env'

export const sessionStore = createSessionStore()

export const apiClient = createApiClient({
  baseUrl: resolveApiBaseUrl(),
  getAccessToken: sessionStore.getAccessToken,
  onUnauthorized: sessionStore.clear,
})

export const authService = createAuthService(apiClient, sessionStore)
