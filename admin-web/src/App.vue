<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  consumeAcademicHandoff,
  hasAcademicSession,
  isAuthenticationError,
  isMockMode,
  logoutAcademic,
  restoreAcademicSession,
} from './api'
import { userMessageForError } from './admin-state'
import AcademicSidebar from './components/AcademicSidebar.vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const authenticated = ref(isMockMode())
const authInitializing = ref(!isMockMode())
const currentUser = ref({ username: 'academic', role: 'ACADEMIC' })
let authLossNotified = false

function unifiedLoginUrl() {
  return import.meta.env.VITE_PORTAL_URL || 'http://127.0.0.1:5173/login'
}

function returnToUnifiedLogin() {
  if (typeof window !== 'undefined') window.location.replace(unifiedLoginUrl())
}

function displayError(error) {
  if (isAuthenticationError(error)) {
    const wasAuthenticated = authenticated.value
    authenticated.value = false
    logoutAcademic()
    if (wasAuthenticated && !authLossNotified) {
      authLossNotified = true
      ElMessage.error('登录已失效，请重新登录')
    }
    returnToUnifiedLogin()
    return
  }
  ElMessage.error(userMessageForError(error))
}

async function initialize() {
  if (isMockMode()) {
    currentUser.value = { username: 'academic', role: 'ACADEMIC' }
    authenticated.value = true
    authInitializing.value = false
    return
  }
  consumeAcademicHandoff()
  if (!hasAcademicSession()) {
    authenticated.value = false
    returnToUnifiedLogin()
    return
  }
  try {
    const user = await restoreAcademicSession()
    currentUser.value = user
    authenticated.value = true
    authLossNotified = false
  } catch (error) {
    authenticated.value = false
    logoutAcademic()
    returnToUnifiedLogin()
  } finally {
    authInitializing.value = false
  }
}

function submitLogout() {
  logoutAcademic()
  authenticated.value = false
  returnToUnifiedLogin()
}

function navigateTo(view) {
  router.push({ name: view })
}

onMounted(initialize)
</script>

<template>
  <main v-if="authInitializing" class="auth-page auth-loading">
    <el-card class="login-card" shadow="never">
      <el-skeleton :rows="4" animated />
    </el-card>
  </main>

  <main v-else-if="!authenticated" class="auth-page">
    <el-card class="login-card" shadow="never">
      <p class="eyebrow">ACADEMIC WEB · ADMIN</p>
      <h1>正在返回统一登录</h1>
      <p class="login-intro">教师端只接受统一登录页验证后的教务会话。</p>
      <el-button type="primary" @click="returnToUnifiedLogin">返回登录页</el-button>
    </el-card>
  </main>

  <div v-else class="app-shell">
    <AcademicSidebar
      :active-view="route.name"
      :user-name="currentUser?.username || '教务老师'"
      :real-api="!isMockMode()"
      @navigate="navigateTo"
      @logout="submitLogout"
    />
    <main class="main-content">
      <header class="topbar">
        <div>
          <span class="topbar-context">教务管理 / {{ route.meta?.title || '课程管理' }}</span>
          <span class="topbar-subtitle">
            {{ route.name === 'courses' ? '维护课程基础信息和开课安排' : '处理课程操作审批并追踪课程变更' }}
          </span>
        </div>
        <div class="topbar-status">
          <el-tag :type="isMockMode() ? 'warning' : 'success'">
            {{ isMockMode() ? 'Mock 模式' : '真实 API' }}
          </el-tag>
        </div>
      </header>
      <router-view />
    </main>
  </div>
</template>
