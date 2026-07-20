<script setup>
import { onMounted, ref } from 'vue'
import AsyncState from '../components/AsyncState.vue'
import { listAuditLogs, listCourses } from '../api/student'
import { errorMessage } from '../api/client'
import { auditActionLabel, auditDescription } from '../utils/audit-display'

const records = ref([])
const courses = ref([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [auditResult, courseResult] = await Promise.allSettled([listAuditLogs(), listCourses()])
    if (auditResult.status === 'rejected') throw auditResult.reason
    records.value = auditResult.value
    courses.value = courseResult.status === 'fulfilled' ? courseResult.value : []
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

function courseForAudit(item) {
  const courseId = item?.after_json?.course_id || item?.before_json?.course_id || item?.resource_id || ''
  return courses.value.find(course => course.id === courseId) || null
}

onMounted(load)
</script>

<template>
  <section>
    <div class="page-title">
      <div><p class="eyebrow">AUDIT TRAIL</p><h1>我的审计记录</h1></div>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-alert title="这里只显示与当前学生本人相关的记录。" type="info" :closable="false" />
    <AsyncState :loading="loading" :error="error" :empty="!records.length" empty-text="暂无本人审计记录" @retry="load">
      <el-timeline>
        <el-timeline-item v-for="item in records" :key="`${item.created_at}-${item.action}-${item.resource_id}`" :timestamp="item.created_at" placement="top">
          <el-card shadow="never">
            <strong>{{ auditActionLabel(item.action) }}</strong>
            <p>{{ auditDescription(item, courseForAudit(item)) }}</p>
            <small>记录编号：{{ item.resource_id }}</small>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </AsyncState>
  </section>
</template>
