import test from 'node:test'
import assert from 'node:assert/strict'
import { API_BASE_URL_STORAGE_KEY, DEVELOPMENT_ENV, normalizeBaseUrl, resolveApiBaseUrl } from '../miniprogram/config/env.ts'

test('MP-23 config: local development endpoint is the running backend API prefix', () => {
  assert.equal(DEVELOPMENT_ENV.apiBaseUrl, 'http://127.0.0.1:8000/api/v1')
  assert.equal(normalizeBaseUrl(DEVELOPMENT_ENV.apiBaseUrl), DEVELOPMENT_ENV.apiBaseUrl)
})

test('MP-23 config: explicit runtime override wins without changing request payloads', () => {
  const previous = globalThis.wx
  globalThis.wx = {
    getStorageSync(key) {
      assert.equal(key, API_BASE_URL_STORAGE_KEY)
      return 'https://api.example.test/api/v1/'
    },
    getAccountInfoSync: () => ({ miniProgram: { envVersion: 'release' } }),
  }
  try {
    assert.equal(resolveApiBaseUrl(), 'https://api.example.test/api/v1')
  } finally {
    globalThis.wx = previous
  }
})

test('MP-23 boundary: invalid runtime URL is rejected before wx.request', () => {
  const previous = globalThis.wx
  globalThis.wx = { getStorageSync: () => 'localhost:8000' }
  try {
    assert.throws(() => resolveApiBaseUrl(), /API_BASE_URL_INVALID/)
  } finally {
    globalThis.wx = previous
  }
})
