<script setup>
import { onMounted, ref } from 'vue'
import AsyncState from '../components/AsyncState.vue'
import { listEnrollments, listWaitlists } from '../api/student'
import { errorMessage } from '../api/client'

const enrollments = ref([]), waitlists = ref([]), loading = ref(false), error = ref('')
async function load() {
  loading.value = true; error.value = ''
  try { [enrollments.value, waitlists.value] = await Promise.all([listEnrollments(), listWaitlists()]) }
  catch (err) { error.value = errorMessage(err) }
  finally { loading.value = false }
}
onMounted(load)
</script>

<template><section>
  <div class="page-title"><div><p class="eyebrow">OVERVIEW</p><h1>我的学习面板</h1></div><el-button @click="load">刷新</el-button></div>
  <AsyncState :loading="loading" :error="error" :empty="false" @retry="load">
    <div class="stat-grid">
      <el-card><p class="stat-label">当前已选</p><strong class="stat-value">{{ enrollments.filter(i => i.status === 'ENROLLED').length }}</strong></el-card>
      <el-card><p class="stat-label">正在候补</p><strong class="stat-value">{{ waitlists.filter(i => i.status === 'WAITING').length }}</strong></el-card>
      <el-card><p class="stat-label">待处理冲突</p><strong class="stat-value danger">{{ enrollments.filter(i => i.status === 'CONFLICT_REVIEW').length }}</strong></el-card>
    </div>
    <div class="quick-grid">
      <router-link to="/recommendations" class="quick-card"><strong>生成课程推荐</strong><span>提交目标，系统自动读取课程表</span></router-link>
      <router-link to="/courses" class="quick-card"><strong>浏览课程</strong><span>查看容量、先修与时段</span></router-link>
      <router-link to="/schedule" class="quick-card"><strong>查看课程表</strong><span>已选课程自动进入课表</span></router-link>
    </div>
  </AsyncState>
</section></template>
