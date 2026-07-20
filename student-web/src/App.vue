<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { clearSession, getCurrentUser } from './auth/session'

const route = useRoute()
const router = useRouter()
const showShell = computed(() => route.path !== '/login')
const user = computed(() => getCurrentUser())

async function logout() {
  clearSession()
  await router.push('/login')
}
</script>

<template>
  <div v-if="showShell" class="app-shell">
    <aside class="sidebar">
      <div class="brand"><span class="brand-mark">AI</span><div><strong>CourseFlow</strong><small>学生端</small></div></div>
      <nav aria-label="学生端导航">
        <router-link to="/dashboard">概览</router-link>
        <router-link to="/recommendations">AI 推荐</router-link>
        <router-link to="/courses">课程目录</router-link>
        <router-link to="/schedule">课程表</router-link>
        <router-link to="/my-enrollments">我的选课</router-link>
        <router-link to="/my-audit-logs">审计记录</router-link>
      </nav>
      <div class="sidebar-footer"><div><strong>{{ user?.username || 'student' }}</strong><small>{{ user?.student_no || 'STUDENT' }}</small></div><el-button text @click="logout">退出</el-button></div>
    </aside>
    <main class="content"><router-view /></main>
  </div>
  <router-view v-else />
</template>
