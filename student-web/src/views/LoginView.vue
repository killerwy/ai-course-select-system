<script setup>
import { reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, register } from '../api/student'
import { errorMessage } from '../api/client'
import { clearSession, saveSession } from '../auth/session'
import { ACADEMIC_ROLE, assertSelectedRole, buildAcademicHandoffUrl, STUDENT_ROLE } from '../auth/role-login'

const router = useRouter()
const selectedRole = ref(STUDENT_ROLE)
const mode = ref('login')
const form = reactive({ username: 'student', password: 'student123', student_no: '', major: '', grade: 2 })
const loading = ref(false)
const roleOptions = [
  { value: STUDENT_ROLE, label: '学生端', hint: '选课、推荐与课程表' },
  { value: ACADEMIC_ROLE, label: '教师端', hint: '课程管理与审批' },
]

watch(selectedRole, (role) => {
  clearSession()
  mode.value = 'login'
  if (role === ACADEMIC_ROLE) Object.assign(form, { username: 'academic', password: 'academic123', student_no: '', major: '', grade: 2 })
  else Object.assign(form, { username: 'student', password: 'student123', student_no: '', major: '', grade: 2 })
})

function selectMode(nextMode) {
  if (selectedRole.value === ACADEMIC_ROLE) return
  mode.value = nextMode
  if (nextMode === 'login') Object.assign(form, { username: 'student', password: 'student123', student_no: '', major: '', grade: 2 })
  else Object.assign(form, { username: '', password: '', student_no: '', major: '', grade: 2 })
}

function validateRegistrationForm() {
  const username = form.username.trim()
  const password = form.password
  const studentNo = form.student_no.trim()
  if (username.length < 3) return '用户名至少需要 3 个字符'
  if (password.length < 6) return '密码至少需要 6 个字符'
  if (!studentNo) return '请填写学号'
  return ''
}

async function submit() {
  if (loading.value) return
  if (mode.value === 'register') {
    const validationError = validateRegistrationForm()
    if (validationError) {
      ElMessage.warning(validationError)
      return
    }
  }
  loading.value = true
  try {
    const result = mode.value === 'register'
      ? await register({ ...form, username: form.username.trim(), student_no: form.student_no.trim(), major: form.major.trim() })
      : await login({ username: form.username.trim(), password: form.password })
    assertSelectedRole(result.user, selectedRole.value)
    if (selectedRole.value === ACADEMIC_ROLE) {
      clearSession()
      ElMessage.success('教师身份验证通过，正在进入教师端')
      const adminUrl = import.meta.env.VITE_ADMIN_WEB_URL || 'http://127.0.0.1:5174'
      window.location.assign(buildAcademicHandoffUrl(adminUrl, result.access_token))
      return
    }
    saveSession(result.access_token, result.user)
    ElMessage.success(mode.value === 'register' ? '注册成功，已进入学生端' : '学生身份验证通过')
    await router.push('/dashboard')
  } catch (error) { ElMessage.error(error?.code === 'ROLE_MISMATCH' ? '账号角色与所选入口不一致' : errorMessage(error, '登录失败')) }
  finally { loading.value = false }
}
</script>

<template>
  <main class="login-page"><section class="login-card unified-login-card">
    <p class="eyebrow">COURSEFLOW · UNIFIED ACCESS</p><h1>统一身份登录</h1>
    <p class="muted">选择入口并使用对应账号登录，系统会校验账号角色后进入学生端或教师端。</p>
    <div class="role-switch" aria-label="选择登录入口">
      <el-radio-group v-model="selectedRole" size="large">
        <el-radio-button v-for="option in roleOptions" :key="option.value" :value="option.value">{{ option.label }}</el-radio-button>
      </el-radio-group>
      <p>{{ roleOptions.find(option => option.value === selectedRole)?.hint }}</p>
    </div>
    <div v-if="selectedRole === 'STUDENT'" class="auth-mode-switch" aria-label="学生账号操作">
      <el-button text :type="mode === 'login' ? 'primary' : 'info'" @click="selectMode('login')">登录</el-button>
      <el-button text :type="mode === 'register' ? 'primary' : 'info'" @click="selectMode('register')">注册学生账号</el-button>
    </div>
    <el-form label-position="top" @submit.prevent="submit">
      <el-form-item label="用户名"><el-input v-model="form.username" autocomplete="username" /></el-form-item>
      <el-form-item label="密码"><el-input v-model="form.password" type="password" show-password autocomplete="current-password" @keyup.enter="submit" /></el-form-item>
      <template v-if="mode === 'register' && selectedRole === 'STUDENT'">
        <el-form-item label="学号"><el-input v-model="form.student_no" autocomplete="off" placeholder="请输入唯一学号" /></el-form-item>
        <el-form-item label="专业（可选）"><el-input v-model="form.major" autocomplete="off" placeholder="例如 计算机科学与技术" /></el-form-item>
        <el-form-item label="年级"><el-input-number v-model="form.grade" :min="1" :max="8" controls-position="right" /></el-form-item>
      </template>
      <el-button class="full-button" type="primary" :loading="loading" @click="submit">{{ mode === 'register' ? '注册并进入学生端' : '登录' }}</el-button>
    </el-form><p class="demo-hint">{{ mode === 'register' ? '注册后会在当前数据库创建独立学生账号，选课和课程表只属于该账号。' : `演示账号：${selectedRole === 'STUDENT' ? 'student / student123' : 'academic / academic123'}` }}</p>
  </section></main>
</template>
