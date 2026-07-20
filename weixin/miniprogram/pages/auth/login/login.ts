import { homeForRole } from '../../../domain/navigation'
import type { Role } from '../../../domain/types'
import { ApiError } from '../../../services/http'
import { authService } from '../../../services/runtime'

interface LoginForm {
  username?: string
  password?: string
  student_no?: string
  major?: string
  grade?: string
}

function messageOf(error: unknown): string {
  return error instanceof ApiError ? error.message : '操作失败，请稍后重试'
}

Page({
  data: {
    role: 'STUDENT' as Role,
    registerMode: false,
    busy: false,
    error: '',
  },
  chooseStudent() {
    this.setData({ role: 'STUDENT', registerMode: false, error: '' })
  },
  chooseAcademic() {
    this.setData({ role: 'ACADEMIC', registerMode: false, error: '' })
  },
  toggleRegister() {
    if (this.data.role !== 'STUDENT') return
    this.setData({ registerMode: !this.data.registerMode, error: '' })
  },
  async submit(event: { detail: { value: LoginForm } }) {
    if (this.data.busy) return
    const value = event.detail.value
    const username = (value.username ?? '').trim()
    const password = value.password ?? ''
    if (username.length < 3 || password.length < 6) {
      this.setData({ error: '用户名至少 3 位，密码至少 6 位' })
      return
    }
    this.setData({ busy: true, error: '' })
    try {
      const session = this.data.registerMode
        ? await authService.register({
          username,
          password,
          student_no: (value.student_no ?? '').trim(),
          major: (value.major ?? '').trim(),
          grade: Number(value.grade ?? 1),
        })
        : await authService.login({ username, password }, this.data.role)
      wx.reLaunch({ url: homeForRole(session.user.role) })
    } catch (error) {
      this.setData({ error: messageOf(error) })
    } finally {
      this.setData({ busy: false })
    }
  },
})
