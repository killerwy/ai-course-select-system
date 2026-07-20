<script setup>
import { RouterLink } from 'vue-router'

defineProps({
  activeView: { type: String, default: 'courses' },
  userName: { type: String, default: '教务老师' },
  realApi: { type: Boolean, default: false },
})

const emit = defineEmits(['logout'])
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-brand">
      <div class="brand-mark">选</div>
      <div>
        <strong>选课教务中心</strong>
        <span>ACADEMIC CONSOLE</span>
      </div>
    </div>

    <div class="sidebar-section-label">工作台</div>
    <nav class="sidebar-nav" aria-label="教务模块">
      <RouterLink
        to="/courses"
        class="sidebar-nav-item"
        :class="{ active: activeView === 'courses' }"
      >
        <span class="nav-icon">▦</span>
        <span>课程管理</span>
      </RouterLink>
      <RouterLink
        to="/approvals"
        class="sidebar-nav-item"
        :class="{ active: activeView === 'approvals' }"
      >
        <span class="nav-icon">✓</span>
        <span>审批中心</span>
      </RouterLink>
      <RouterLink
        to="/audits"
        class="sidebar-nav-item"
        :class="{ active: activeView === 'audits' }"
      >
        <span class="nav-icon">☰</span>
        <span>审计日志</span>
      </RouterLink>
      <RouterLink
        to="/runs"
        class="sidebar-nav-item"
        :class="{ active: activeView === 'runs' }"
      >
        <span class="nav-icon">↻</span>
        <span>重算记录</span>
      </RouterLink>
    </nav>

    <div class="sidebar-footer">
      <div class="user-card">
        <div class="avatar">{{ userName.slice(0, 1).toUpperCase() }}</div>
        <div class="user-card-copy">
          <strong>{{ userName }}</strong>
          <span>{{ realApi ? '真实 API' : '演示模式' }}</span>
        </div>
        <el-button text class="logout-button" aria-label="退出登录" @click="emit('logout')">↪</el-button>
      </div>
    </div>
  </aside>
</template>
