import axios from 'axios'
import { clearSession, getToken } from '../auth/session'

export const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 10000,
})

const registrationFieldLabels = Object.freeze({ username: '用户名', password: '密码', student_no: '学号', major: '专业', grade: '年级' })

function validationDetailMessage(detail) {
  if (!Array.isArray(detail) || !detail.length) return ''
  const item = detail[0] || {}
  const location = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : ''
  const field = registrationFieldLabels[location] || '注册信息'
  if (item.type === 'string_too_short') {
    const minimum = item.ctx?.min_length
    return minimum ? `${field}至少需要 ${minimum} 个字符` : `${field}长度不符合要求`
  }
  if (item.type === 'missing') return `请填写${field}`
  if (item.type === 'greater_than_equal' || item.type === 'less_than_equal') return `${field}取值范围不合法`
  return `${field}格式不正确，请检查后再提交`
}

client.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

client.interceptors.response.use(
  response => response,
  (error) => {
    if (error?.response?.status === 401) clearSession()
    const body = error?.response?.data
    error.apiError = body?.error || {
      code: body?.detail ? 'API_ERROR' : 'NETWORK_ERROR',
      message: typeof body?.detail === 'string' ? body.detail : (validationDetailMessage(body?.detail) || body?.detail?.decision || error.message || '网络请求失败'),
      details: Array.isArray(body?.detail) ? body.detail : [],
    }
    return Promise.reject(error)
  },
)

export const enrollmentDecisionMessages = Object.freeze({
  DUPLICATE: '已选过该课程，不能重复选课。',
  CONFLICT: '时间冲突：该课程与已选课程的上课时间重叠，不能选课。',
  TIME_CONFLICT: '时间冲突：该课程与已选课程的上课时间重叠，不能选课。',
  PREREQUISITE_MISSING: '缺少前置课程：请先完成要求的前置课程后再选课。',
  CAPACITY_FULL: '课程已满，当前不能直接选课，可以加入候补。',
  WAITLIST_ALLOWED: '课程已满，可以加入候补。',
  COURSE_CLOSED: '课程已关闭，暂时不能选课。',
  COURSE_CANCELLED: '课程已取消，不能选课。',
  EXCEPTION_REQUIRED: '当前选课需要审批，请先提交审批申请。',
})

export function errorMessage(error, fallback = '请求失败') {
  const detail = error?.response?.data?.detail
  const apiError = error?.apiError || {}
  const candidates = [
    typeof detail === 'object' ? detail?.decision : detail,
    apiError.code,
    apiError.message,
  ]
  const decision = candidates.find(value => typeof value === 'string' && enrollmentDecisionMessages[value.toUpperCase()])
  if (decision) return enrollmentDecisionMessages[decision.toUpperCase()]
  const validationMessage = validationDetailMessage(detail)
  if (validationMessage) return validationMessage
  if (typeof apiError.message === 'string' && apiError.message.trim()) return apiError.message
  if (typeof detail === 'string' && detail.trim()) return detail
  return fallback
}

// 兼容主项目当前 memory 模式的裸数据，以及 MySQL 模式的 { data, meta } 契约。
export function unwrapResponse(response) {
  const payload = response?.data
  if (payload && Object.hasOwn(payload, 'data')) return payload.data
  return payload
}
